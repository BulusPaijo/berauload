"""Column catalog and cell resolvers for the gardu export builder (9d-2)."""
from fastapi import HTTPException
from ..org_units.models import OrgUnit
from .models import (Substation, SubstationField, SubstationMeasurement, SubstationParam,
                     SubstationSession, SubstationValue)
from .models_calc import GarduCalcColumn, GarduCalcRule
from .analysis_queries import reference

IDENT = [('code', 'Kode gardu'), ('name', 'Nama gardu'), ('feeder', 'Penyulang'), ('unit', 'Unit'),
         ('address', 'Alamat'), ('ownership', 'Kepemilikan'), ('purpose', 'Peruntukan'),
         ('brand', 'Merk'), ('tap', 'Tap'), ('serial_number', 'Nomor seri'), ('year', 'Tahun'),
         ('lat', 'Latitude'), ('lon', 'Longitude')]
TRAFO = [('power_kva', 'Daya (kVA)'), ('phase', 'Fase'), ('line_count', 'Jumlah jurusan'),
         ('line_labels', 'Nama jurusan')]
VISIT = [('measured_on', 'Tanggal ukur'), ('session', 'Sesi'), ('measured_at', 'Jam'),
         ('technician', 'Petugas'), ('note', 'Catatan'), ('state', 'Status verifikasi'),
         ('revision', 'Revisi'), ('status', 'Status ukur'), ('last_measured_on', 'Pengukuran terakhir'),
         ('age_days', 'Umur pengukuran (hari)')]
SORTABLE = {'code', 'name', 'feeder', 'power_kva', 'measured_on', 'session', 'state', 'brand', 'address'}
MAX_COLUMNS = 60


def catalog(db):
    items = [dict(key=k, label=l, group='Identitas gardu') for k, l in IDENT]
    items += [dict(key='extra:' + f.code, label=f.name, group='Identitas gardu')
              for f in db.query(SubstationField).filter_by(active=True).order_by(SubstationField.display_order)]
    items += [dict(key=k, label=l, group='Trafo') for k, l in TRAFO]
    items += [dict(key=k, label=l, group='Pengukuran') for k, l in VISIT]
    for p in db.query(SubstationParam).filter_by(active=True).order_by(SubstationParam.display_order):
        lines = [0] if p.scope == 'substation' else [1, 2, 3, 4, 5]
        for n in lines:
            suffix = '' if n == 0 else f' J{n}'
            items.append(dict(key=f'param:{p.code}:{n}', label=f'{p.name}{suffix} ({p.unit})',
                              group='Nilai ukur', param=p.code, line=n))
    for c in db.query(GarduCalcColumn).filter_by(active=True).order_by(GarduCalcColumn.display_order):
        items.append(dict(key='calc:' + c.code, label=f'{c.name} ({c.unit})' if c.unit else c.name,
                          group='Hasil hitung'))
    rules = db.query(GarduCalcRule).filter_by(active=True).order_by(GarduCalcRule.display_order).all()
    items.append(dict(key='category', label='Kategori (utama)', group='Hasil hitung'))
    for g in dict.fromkeys(r.group_name for r in rules if r.kind == 'category'):
        items.append(dict(key='category:' + g, label=f'Kategori — {g}', group='Hasil hitung'))
    items.append(dict(key='findings', label='Temuan (daftar)', group='Hasil hitung'))
    items += [dict(key='finding:' + r.code, label=f'Temuan: {r.name}', group='Hasil hitung')
              for r in rules if r.kind == 'finding']
    items.append(dict(key='definition_version', label='Versi definisi hasil', group='Hasil hitung'))
    items += [dict(key='followup_type', label='Tindak lanjut — jenis', group='Tindak lanjut'),
              dict(key='followup_status', label='Tindak lanjut — status', group='Tindak lanjut'),
              dict(key='followup_assignee', label='Tindak lanjut — penanggung jawab', group='Tindak lanjut'),
              dict(key='followup_due', label='Tindak lanjut — target', group='Tindak lanjut')]
    ref = reference(db)
    if ref:
        items += [dict(key='sesi:' + s.code, label=f'{ref.name} — {s.name}', group='Sesi berdampingan')
                  for s in db.query(SubstationSession).filter_by(active=True).order_by(SubstationSession.display_order)]
    return items


def resolve_keys(db, columns):
    """Validate spec columns -> ordered [(key,header)]; unknown/archived key -> 422."""
    if not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS:
        raise HTTPException(422, f'Pilih 1 sampai {MAX_COLUMNS} kolom')
    known = {i['key']: i['label'] for i in catalog(db)}
    out = []
    for col in columns:
        key = col.get('key') if isinstance(col, dict) else None
        if key not in known:
            raise HTTPException(422, f'Kolom tidak dikenal atau diarsipkan: {str(key)[:60]}')
        header = (col.get('header') or '').strip() or known[key]
        if len(header) > 80:
            raise HTTPException(422, 'Judul kolom maksimal 80 karakter')
        out.append((key, header))
    if len({k for k, _ in out}) != len(out):
        raise HTTPException(422, 'Kolom ganda dalam susunan')
    return out


def missing_keys(db, columns):
    known = {i['key'] for i in catalog(db)}
    return [c.get('key') for c in columns if isinstance(c, dict) and c.get('key') not in known]


class Context:
    """Per-chunk lookups so cell resolution never queries per cell."""

    def __init__(self, db, rows):
        sids = [r['id'] for r in rows]
        mids = [r['measurement_id'] for r in rows if r['measurement_id']]
        self.st = {s.id: s for s in db.query(Substation).filter(Substation.id.in_(sids))}
        self.visit = {m.id: m for m in db.query(SubstationMeasurement).filter(SubstationMeasurement.id.in_(mids))} if mids else {}
        self.units = {u.id: u.name for u in db.query(OrgUnit.id, OrgUnit.name)}
        self.values = {}
        if mids:
            for v in db.query(SubstationValue).filter(SubstationValue.measurement_id.in_(mids)):
                self.values[(v.measurement_id, v.param_id, v.line_no)] = v
        self.params = {p.code: p for p in db.query(SubstationParam)}
        self.decimals = {c.code: c.decimals for c in db.query(GarduCalcColumn.code, GarduCalcColumn.decimals)}


def cell(key, row, ctx):
    st, visit = ctx.st[row['id']], ctx.visit.get(row['measurement_id'])
    kind, _, rest = key.partition(':')
    if kind == 'param':
        code, _, line = rest.rpartition(':')
        p = ctx.params.get(code)
        v = ctx.values.get((row['measurement_id'], p.id, int(line))) if p else None
        return None if v is None else (v.flag if v.flag else (float(v.value) if v.value is not None else None))
    if kind == 'calc':
        c = row['columns'].get(rest)
        if not c or c['value'] is None:
            return None
        places = ctx.decimals.get(rest)
        return round(c['value'], places) if isinstance(places, int) else c['value']
    if kind == 'finding':
        return 'Ya' if any(f['code'] == rest for f in row['findings']) else None
    if kind == 'sesi':
        return row['sessions'].get(rest)
    if kind == 'extra':
        return (st.extra_values or {}).get(rest)
    if key == 'category':
        return row['category']['name']
    if kind == 'category':
        found = next((c['name'] for c in row['categories'] if c['group_name'] == rest), None)
        return found
    if key == 'findings':
        return ', '.join(f['name'] for f in row['findings']) or None
    if key.startswith('followup_'):
        f = row.get('followup') or {}
        return f.get({'followup_type': 'type', 'followup_status': 'status', 'followup_assignee': 'assignee', 'followup_due': 'due_on'}[key])
    if key == 'definition_version':
        return row['result_version']
    if key == 'unit':
        return ctx.units.get(st.unit_id)
    if key == 'feeder':
        return row['feeder']
    if key == 'line_labels':
        return ' | '.join(st.line_labels or []) or None
    if key in ('lat', 'lon', 'power_kva'):
        v = getattr(st, key)
        return None if v is None else float(v)
    if key in ('measured_on', 'last_measured_on'):
        return row[key]
    if key in ('measured_at', 'technician', 'note', 'revision'):
        return getattr(visit, key, None) if visit else None
    if key in ('session', 'state', 'status', 'age_days'):
        return row[key]
    return getattr(st, key, None)
