"""Atomic per-visit writes, revisions, snapshot preservation and audit."""
from datetime import datetime, timezone
import hashlib
from sqlalchemy import text
from fastapi import HTTPException
from sqlalchemy import select
from ...db import User, AuditLog, now
from .common import audit, as_number, data_units, dump, ensure_owner
from .models import (Substation, SubstationMeasurement, SubstationParam,
                     SubstationValue, SubstationValueFlag, SubstationSession)


def values_for(db, visit_id):
    return [dump(row) for row in db.query(SubstationValue).filter_by(
        measurement_id=visit_id).order_by(SubstationValue.param_id,
                                          SubstationValue.line_no)]


def detail(db, visit):
    result = dump(visit)
    result['values'] = values_for(db, visit.id)
    result['updated_by_name'] = db.get(User, visit.updated_by).display_name if visit.updated_by else None
    return result


def conflict(db, visit):
    raise HTTPException(409, {'reason': 'Pengukuran telah diubah pengguna lain',
                              'server': detail(db, visit),
                              'updated_by': visit.updated_by,
                              'updated_at': visit.updated_at.isoformat() if visit.updated_at else None})


def check_value(db, line_count, param, data, flags):
    line_no = data.line_no
    if param.scope == 'line' and not 1 <= line_no <= line_count:
        raise HTTPException(422, f'{param.code}: nomor jurusan di luar 1..{line_count}')
    if param.scope == 'substation' and line_no != 0:
        raise HTTPException(422, f'{param.code}: nomor jurusan harus 0')
    flag = data.flag
    if flag and flag not in flags:
        raise HTTPException(422, f'Flag {flag} tidak terdaftar')
    if flag and data.value is not None:
        raise HTTPException(422, f'{param.code}: pilih angka ATAU flag, bukan keduanya')
    value = as_number(data.value, param.code, low=0) if data.value is not None else None
    # min/max are soft warnings; do not reject potentially real measurements.
    warning = None
    if value is not None and ((param.min_value is not None and value < param.min_value) or
                              (param.max_value is not None and value > param.max_value)):
        warning = f'{param.code}: nilai di luar batas wajar'
    return value, flag, warning


def save_visit(db, ctx, body, fill_empty=False, calc_prepared=None):
    master = db.get(Substation, body.substation_id)
    if not master or master.unit_id not in data_units(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan pada unit aktif atau KP di bawahnya')
    session = db.query(SubstationSession).filter_by(code=body.session, active=True).first()
    if session is None:
        raise HTTPException(422, 'Sesi pengukuran tidak dikenal atau tidak aktif')
    if db.bind.dialect.name == 'postgresql':
        identity = f'{master.unit_id}:{master.id}:{body.measured_on}:{body.session}'
        digest = hashlib.sha256(identity.encode()).digest()
        lock_key = int.from_bytes(digest[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_key})
    query = db.query(SubstationMeasurement).filter_by(
        substation_id=master.id, measured_on=body.measured_on, session=body.session)
    if db.bind.dialect.name == 'postgresql':
        query = query.with_for_update()
    visit = query.first()
    if visit and visit.state != 'draft':
        raise HTTPException(409, 'Pengukuran verified terkunci')
    if visit and (body.revision is None or body.revision != visit.revision):
        conflict(db, visit)
    if not visit and body.revision is not None:
        raise HTTPException(409, 'Pengukuran baru tidak memiliki revision')
    old = detail(db, visit) if visit else None
    if not visit:
        visit = SubstationMeasurement(unit_id=master.unit_id, substation_id=master.id,
            measured_on=body.measured_on, session=body.session,
            snapshot_power_kva=master.power_kva, snapshot_phase=master.phase,
            snapshot_line_count=master.line_count, snapshot_feeder_id=master.feeder_id,
            created_by=ctx.actor.id, updated_by=ctx.actor.id)
        db.add(visit); db.flush()
    patches = {(v.code, v.line_no): v for v in body.values}
    if len(patches) != len(body.values):
        raise HTTPException(422, 'Parameter dan jurusan duplikat')
    params = {p.code: p for p in db.query(SubstationParam).filter_by(active=True)}
    flags = {f.code for f in db.query(SubstationValueFlag).filter_by(active=True)}
    warnings = []
    for (code, line), item in patches.items():
        param = params.get(code)
        if param is None:
            raise HTTPException(422, f'Parameter {code} tidak aktif atau tidak ada')
        value, flag, warning = check_value(db, visit.snapshot_line_count, param, item, flags)
        if warning:
            warnings.append(warning)
        row = db.query(SubstationValue).filter_by(measurement_id=visit.id,
                                                param_id=param.id, line_no=line).first()
        if fill_empty and row and (row.value is not None or row.flag):
            continue
        if value is None and not flag:
            if row:
                db.delete(row)
        elif row:
            row.value, row.flag = value, flag
        else:
            db.add(SubstationValue(measurement_id=visit.id, param_id=param.id,
                                   line_no=line, value=value, flag=flag))
    for key in ('measured_at', 'technician', 'note'):
        incoming = getattr(body, key)
        if incoming is not None and not fill_empty:
            setattr(visit, key, incoming)
        elif incoming is not None and getattr(visit, key) is None:
            setattr(visit, key, incoming)
    db.flush()
    new = detail(db, visit)
    changed = old is None or any(old[key] != new[key] for key in (
        'values', 'technician', 'measured_at', 'note'))
    if changed:
        if old is not None:
            visit.revision += 1
        visit.updated_by, visit.updated_at = ctx.actor.id, now()
        audit(db, ctx, 'substation_visit_save', visit.id, old, detail(db, visit))
    if changed:
        from .calculation_service import save_results
        save_results(db, visit, prepared=calc_prepared)
    from .calculation_service import get_results
    return {'id': visit.id, 'revision': visit.revision,
            'status': 'saved' if changed else 'unchanged', 'warnings': warnings,
            'measurement': detail(db, visit),
            'calculated': get_results(db, visit.id)}
