"""Safe XLSX/CSV parsing, preview staging, formula-injection-safe templates."""
import csv
import io
import json
import os
import secrets
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Protection
from .common import as_number, dump
from .models import (Substation, SubstationFeeder, SubstationParam,
                     SubstationSession, SubstationValueFlag)

MAX_FILE = 4 * 1024 * 1024
STAGING = Path(os.getenv('UPLOAD_DIR', '/data/uploads')) / 'substations_preview'


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def workbook_bytes(rows, headers, title):
    book = Workbook()
    sheet = book.active
    sheet.title = title[:31]
    sheet.append([safe_cell(h) for h in headers])
    for row in rows:
        sheet.append([safe_cell(item) for item in row])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def parse_uploaded(content, filename):
    if len(content) > MAX_FILE:
        raise HTTPException(413, 'File melebihi batas 4 MB')
    if filename.lower().endswith('.csv'):
        try:
            text = content.decode('utf-8-sig')
            return list(csv.reader(io.StringIO(text)))[:5002]
        except UnicodeError:
            raise HTTPException(422, 'CSV harus UTF-8')
    if not filename.lower().endswith('.xlsx'):
        raise HTTPException(422, 'Hanya Excel .xlsx atau CSV yang diterima')
    try:
        # Prevent tiny ZIP archives from inflating into huge XLSX XML workloads.
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 1000 or sum(m.file_size for m in members) > 24 * 1024 * 1024:
                raise HTTPException(413, 'Isi Excel terlalu besar setelah ekstraksi')
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheet = book.active
        rows = []
        for row in sheet.iter_rows(max_row=5002, values_only=True):
            if any(isinstance(cell, str) and cell.startswith('=') for cell in row):
                raise HTTPException(422, 'Formula Excel tidak diizinkan pada input')
            rows.append([str(value).strip() if value is not None else '' for value in row])
        book.close()
        return rows
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, 'Berkas Excel tidak dapat dibaca')


def stage_preview(actor_id, unit_id, kind, payload):
    STAGING.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = secrets.token_hex(24)
    path = STAGING / (token + '.json')
    path.write_text(json.dumps({'actor_id': actor_id, 'unit_id': unit_id,
                   'kind': kind, 'expires': (datetime.now(timezone.utc) +
                   timedelta(minutes=30)).isoformat(), 'payload': payload}), encoding='utf-8')
    os.chmod(path, 0o600)
    return token


def load_stage(token, actor_id, unit_id, kind):
    if len(token) != 48 or any(char not in '0123456789abcdef' for char in token):
        raise HTTPException(404, 'Pratinjau tidak ditemukan')
    path = STAGING / (token + '.json')
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(404, 'Pratinjau tidak ditemukan atau kedaluwarsa')
    if (obj['actor_id'] != actor_id or obj['unit_id'] != unit_id or
            obj['kind'] != kind or
            datetime.fromisoformat(obj['expires']) < datetime.now(timezone.utc)):
        raise HTTPException(403, 'Pratinjau tidak berlaku untuk pengguna/unit ini')
    return obj['payload'], path


def unit_codes(db, unit_ids):
    from ..org_units.models import OrgUnit
    return {u.code: u.id for u in db.query(OrgUnit).filter(OrgUnit.id.in_(unit_ids))}


def master_template(db, unit_ids, feeder_unit_ids):
    """9d-4: column 'unit' (kode ULP/KP) lets an ULP place gardu in its KPs."""
    headers = ['kode', 'nama', 'penyulang', 'ownership', 'address', 'tap',
               'phase', 'brand', 'power_kva', 'serial_number', 'year', 'purpose',
               'lat', 'lon', 'line_count', 'line_labels', 'unit']
    feeders = {row.id: row.code for row in db.query(SubstationFeeder).filter(
        SubstationFeeder.unit_id.in_(feeder_unit_ids))}
    codes = {v: k for k, v in unit_codes(db, unit_ids).items()}
    rows = []
    for s in db.query(Substation).filter(Substation.unit_id.in_(unit_ids)).order_by(Substation.code):
        rows.append([s.code, s.name, feeders.get(s.feeder_id, ''), s.ownership,
                     s.address, s.tap, s.phase, s.brand, float(s.power_kva),
                     s.serial_number, s.year, s.purpose,
                     float(s.lat) if s.lat is not None else None,
                     float(s.lon) if s.lon is not None else None,
                     s.line_count, '|'.join(s.line_labels or []), codes.get(s.unit_id, '')])
    return workbook_bytes(rows, headers, 'Master Gardu')


def master_preview(db, unit_ids, rows, feeder_unit_ids):
    if not rows:
        raise HTTPException(422, 'File kosong')
    header = [str(h).strip().lower() for h in rows[0]]
    if not {'kode', 'nama', 'power_kva', 'phase', 'line_count'}.issubset(header):
        raise HTTPException(422, 'Kolom kode, nama, power_kva, phase, line_count wajib')
    feeders = {f.code: f.id for f in db.query(SubstationFeeder).filter(
        SubstationFeeder.unit_id.in_(feeder_unit_ids))}
    existing = {s.code for s in db.query(Substation).filter(Substation.unit_id.in_(unit_ids))}
    units = unit_codes(db, unit_ids)
    parsed, new_feeders, seen = [], set(), set()
    for number, row in enumerate(rows[1:], 2):
        if not any(str(x).strip() for x in row):
            continue
        data = dict(zip(header, [str(x).strip() for x in row]))
        code = data.get('kode', '')
        errors = []
        if not code or code in seen:
            errors.append('Kode kosong atau duplikat di berkas')
        seen.add(code)
        feeder = data.get('penyulang') or ''
        if feeder and feeder not in feeders:
            new_feeders.add(feeder)
        values = {'code': code, 'name': data.get('nama'), 'feeder_code': feeder}
        if data.get('unit'):
            if data['unit'] not in units:
                errors.append(f"Unit '{data['unit']}' bukan ULP aktif atau KP di bawahnya")
            else:
                values['unit_id'] = units[data['unit']]
        for attr in ('power_kva', 'phase', 'line_count', 'lat', 'lon', 'year'):
            if data.get(attr):
                try:
                    raw = data[attr].replace(',', '.')
                    values[attr] = int(raw) if attr in ('phase', 'line_count', 'year') else float(raw)
                except ValueError:
                    errors.append(f'{attr} bukan angka')
        for src, dest in (('ownership','ownership'), ('address','address'),
                          ('tap','tap'), ('brand','brand'),
                          ('serial_number','serial_number'), ('purpose','purpose')):
            if data.get(src):
                values[dest] = data[src]
        values['line_labels'] = data.get('line_labels', '').split('|') if data.get('line_labels') else []
        if not values.get('name') or values.get('power_kva', 0) <= 0 or values.get('phase') not in (1,3) or values.get('line_count') not in range(1,6):
            errors.append('Nama, daya, fase atau jumlah jurusan tidak valid')
        parsed.append({'row': number, 'action': 'update' if code in existing else 'create',
                       'values': values, 'errors': errors})
    return {'rows': parsed, 'new_feeders': sorted(new_feeders)}


def measurement_template(db, unit_ids, feeder_id=None, day=None, session=None):
    params = db.query(SubstationParam).filter_by(active=True).order_by(SubstationParam.display_order).all()
    headers = ['kode', 'tanggal', 'sesi', 'petugas', 'jam']
    for param in params:
        headers.extend([param.code + ':J' + str(i) for i in range(1, 6)] if
                       param.scope == 'line' else [param.code])
    query = db.query(Substation).filter(Substation.unit_id.in_(unit_ids), Substation.active.is_(True))
    if feeder_id:
        query = query.filter_by(feeder_id=feeder_id)
    book = Workbook(); sheet = book.active; sheet.title = 'Pengukuran Gardu'
    sheet.append(headers)
    for master in query.order_by(Substation.code):
        row = [safe_cell(master.code), day.isoformat() if day else '', session or '', '', '']
        for param in params:
            row.extend([''] * (5 if param.scope == 'line' else 1))
        sheet.append(row)
        index = sheet.max_row
        for col_index, name in enumerate(headers, 1):
            sheet.cell(index,col_index).protection = Protection(locked=False)
            if ':J' in name and int(name.rsplit(':J', 1)[-1]) > master.line_count:
                cell = sheet.cell(index, col_index)
                cell.fill = PatternFill('solid', fgColor='D9DDE4')
                cell.protection = Protection(locked=True)
    sheet.protection.sheet = True
    result = io.BytesIO(); book.save(result)
    return result.getvalue()


def measurement_preview(db, unit_ids, rows):
    if not rows:
        raise HTTPException(422, 'File kosong')
    headers = [str(h).strip() for h in rows[0]]
    if not {'kode', 'tanggal', 'sesi'}.issubset(headers):
        raise HTTPException(422, 'Kolom kode, tanggal, sesi wajib')
    masters = {row.code: row for row in db.query(Substation).filter(Substation.unit_id.in_(unit_ids))}
    params = {p.code: p for p in db.query(SubstationParam).filter_by(active=True)}
    flags = {f.code: f.code for f in db.query(SubstationValueFlag).filter_by(active=True)}
    flags.update({f.name.upper(): f.code for f in db.query(SubstationValueFlag).filter_by(active=True)})
    parsed = []
    for index, row in enumerate(rows[1:], 2):
        data = dict(zip(headers, row))
        if not any(str(x).strip() for x in row):
            continue
        master = masters.get(str(data.get('kode', '')).strip())
        errors = []
        if master is None:
            errors.append('Gardu tidak ditemukan di unit ini')
        values = []
        for label, value in data.items():
            if label in ('kode','tanggal','sesi','petugas','jam') or value in ('', None):
                continue
            code, _, line = label.partition(':J')
            param = params.get(code)
            if not param or (param.scope == 'line' and not line) or (param.scope == 'substation' and line) or (line and (not line.isdigit() or not master or int(line) > master.line_count)):
                errors.append(f'Kolom {label} tidak valid untuk gardu')
                continue
            text = str(value).strip()
            flag = flags.get(text.upper())
            try:
                number = None if flag else float(text.replace(',', '.'))
                if not flag and (number < 0 or not __import__('math').isfinite(number)):
                    raise ValueError()
            except ValueError:
                errors.append(f'{label}: bukan angka atau flag')
                continue
            values.append({'code': code, 'line_no': int(line) if line else 0,
                           'value': number, 'flag': flag})
        try:
            day = date.fromisoformat(str(data.get('tanggal', '')).strip()).isoformat()
        except ValueError:
            errors.append('Tanggal harus YYYY-MM-DD'); day = ''
        parsed.append({'row': index, 'values': {'substation_id': master.id if master else -1,
              'measured_on': day, 'session': str(data.get('sesi','')).strip(),
              'technician': str(data.get('petugas','')).strip() or None,
              'measured_at': str(data.get('jam','')).strip() or None,
              'values': values}, 'errors': errors})
    return {'rows': parsed}
