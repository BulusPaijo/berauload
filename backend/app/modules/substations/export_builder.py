"""Export builder engine: bounded chunks, temp-file output (no full result in memory)."""
import csv
import json
import os
import re
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import func
from openpyxl import Workbook
from .analysis_data import decorate
from .analysis_export import clean
from .analysis_queries import sorted_query
from .export_catalog import Context, SORTABLE, cell, resolve_keys
from .models import SubstationValue
from .models_calc import GarduCalcColumn, GarduCalcRule, GarduCalcSettings

MAX_WIDE = 50000
MAX_LONG = 200000
CHUNK = 200
PREVIEW = 20
def safe(value):
    """Empty stays truly empty (None), never '' or 0; text is injection-sanitized."""
    return None if value is None else clean(value)


LONG_TAIL = ['Parameter', 'Satuan', 'Jurusan', 'Nilai', 'Penanda']


def check_spec(db, spec):
    if not isinstance(spec, dict):
        raise HTTPException(422, 'Spesifikasi ekspor tidak sah')
    shape = spec.get('shape', 'wide')
    if shape not in ('wide', 'long'):
        raise HTTPException(422, 'Bentuk data harus wide atau long')
    fmt = spec.get('format', 'xlsx')
    if fmt not in ('xlsx', 'csv'):
        raise HTTPException(422, 'Format harus xlsx atau csv')
    delim = spec.get('delimiter', ';')
    if delim not in (';', ','):
        raise HTTPException(422, 'Pemisah CSV harus ; atau ,')
    keys = resolve_keys(db, spec.get('columns'))
    if shape == 'long' and any(k.startswith('param:') for k, _ in keys):
        raise HTTPException(422, 'Bentuk panjang tidak memakai kolom nilai ukur lebar')
    return keys, shape, fmt, delim


def total_rows(db, query, shape):
    sub = query.order_by(None).subquery()
    if shape == 'long':
        return db.query(func.count(SubstationValue.id)).join(
            sub, sub.c.mid == SubstationValue.measurement_id).scalar() or 0
    return db.query(func.count()).select_from(sub).scalar() or 0


def generate(db, query, opt, keys, shape, limit=None):
    """Yield data rows; long shape yields one row per stored value."""
    if opt.sort not in SORTABLE and not opt.sort.startswith('extra_'):
        if not db.query(GarduCalcColumn.id).filter_by(code=opt.sort, active=True).first():
            raise HTTPException(422, 'Kolom sortir tidak dikenal')
    # Run the ranked/filtered relation ONCE (light key tuples only), then decorate
    # in small chunks; re-running it per OFFSET chunk made 5k rows take 22 s.
    keys_only = sorted_query(db, query, opt).all()
    count = 0
    for offset in range(0, len(keys_only), CHUNK):
        batch = keys_only[offset:offset + CHUNK]
        rows = decorate(db, batch)
        ctx = Context(db, rows)
        for row in rows:
            base = [safe(cell(k, row, ctx)) for k, _ in keys]
            if shape == 'wide':
                yield base
                count += 1
            else:
                pid = {p.id: p for p in ctx.params.values()}
                vals = sorted(((m, p, ln) for (m, p, ln) in ctx.values if m == row['measurement_id']),
                              key=lambda t: (pid[t[1]].display_order, t[2]))
                for m, p, ln in vals:
                    v = ctx.values[(m, p, ln)]
                    yield base + [safe(pid[p].name), safe(pid[p].unit), 'Gardu' if ln == 0 else ln,
                                  float(v.value) if v.value is not None else None, safe(v.flag)]
                    count += 1
            if limit and count >= limit:
                return


def notes(db, opt, keys, shape, total):
    settings = db.get(GarduCalcSettings, 1)
    cols = {c.code: c for c in db.query(GarduCalcColumn)}
    info = [('Dibuat pada', datetime.now(ZoneInfo('Asia/Makassar')).isoformat()),
            ('Bentuk data', 'Satu baris per nilai ukur (panjang)' if shape == 'long' else 'Satu baris per gardu/pengukuran (lebar)'),
            ('Jumlah baris', total), ('Versi definisi', settings.version if settings else None),
            ('Filter', json.dumps(opt.model_dump(mode='json'), ensure_ascii=False)),
            ('Catatan', 'Sel kosong berarti tidak ada nilai (bukan nol).'),
            ('Pembulatan', 'Kolom hitung dibulatkan sesuai desimal di Rumus & Kategori; nilai ukur apa adanya.')]
    for key, header in keys:
        if key.startswith('calc:') and key[5:] in cols:
            info.append((f'Rumus {header}', cols[key[5:]].expression))
    used = any(k in ('category', 'findings') or k.startswith(('category:', 'finding:')) for k, _ in keys)
    if used:
        for r in db.query(GarduCalcRule).filter_by(active=True).order_by(GarduCalcRule.display_order):
            info.append((f'Aturan {r.kind} {r.name}', r.expression))
    return info


def write_file(db, query, opt, keys, shape, fmt, delim, total):
    """Write to a temp file in chunks; caller returns FileResponse and deletes it."""
    headers = [clean(h) for _, h in keys] + (LONG_TAIL if shape == 'long' else [])
    note_rows = notes(db, opt, keys, shape, total)
    fd, path = tempfile.mkstemp(suffix='.' + fmt)
    os.close(fd)
    try:
        if fmt == 'csv':
            with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
                w = csv.writer(fh, delimiter=delim)
                w.writerow(headers)
                for row in generate(db, query, opt, keys, shape):
                    w.writerow(row)
                w.writerow([])
                w.writerow(['KETERANGAN', 'Nilai'])
                for a, b in note_rows:
                    w.writerow([clean(a), clean(b)])
        else:
            wb = Workbook(write_only=True)
            sheet = wb.create_sheet('Data Gardu')
            sheet.append(headers)
            for row in generate(db, query, opt, keys, shape):
                sheet.append(row)
            info = wb.create_sheet('Keterangan')
            for a, b in note_rows:
                info.append([clean(a), clean(b)])
            wb.save(path)
    except Exception:
        os.unlink(path)
        raise
    return path


def filename(brand, fmt):
    slug = re.sub('[^a-zA-Z0-9_-]+', '-', brand or '')[:30].strip('-') or 'BerauLoad'
    return f'{slug}_Export_Gardu_{datetime.now().strftime("%Y%m%d")}.{fmt}'
