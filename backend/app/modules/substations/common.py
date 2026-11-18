"""Shared authorization, validation, serialization and audit for visit data."""
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from sqlalchemy import or_
from ...db import AuditLog, now
from ..org_units.models import OrgUnit
from .models import Substation, SubstationChoice, SubstationFeeder, SubstationField

CODE = re.compile(r'^[A-Za-z][A-Za-z0-9_\-]{0,79}$')
MASTER_FIELDS = ('code', 'name', 'feeder_id', 'ownership', 'address', 'tap',
                 'phase', 'brand', 'power_kva', 'serial_number', 'year', 'purpose',
                 'lat', 'lon', 'line_count', 'line_labels', 'extra_values', 'active')
TRAFO_FIELDS = {'phase', 'power_kva', 'brand', 'serial_number', 'tap'}


def json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def dump(row, fields=None):
    if fields is None:
        fields = [col.name for col in row.__table__.columns]
    return {key: json_value(getattr(row, key)) for key in fields}


def audit(db, ctx, action, target, before=None, after=None, **extra):
    role = 'admin_global' if ctx.superadmin else ','.join(sorted(ctx.roles))
    db.add(AuditLog(user_id=ctx.actor.id, action=action, target=str(target),
                    detail={'unit_id': ctx.id, 'actor_role': role,
                            'before': before, 'after': after, **extra}))


def check_code(code):
    if not CODE.fullmatch(code):
        raise HTTPException(422, 'Kode harus dimulai huruf dan hanya memakai huruf/angka/_/-')
    return code


def child_ids(db, ctx):
    """Read inheritance, never the parent or sibling of a KP."""
    result = [ctx.id]
    queue = [ctx.id]
    while queue:
        rows = db.query(OrgUnit.id).filter(
            OrgUnit.parent_id.in_(queue), OrgUnit.active.is_(True)).all()
        queue = [row[0] for row in rows]
        result.extend(queue)
    return result


def data_units(db, ctx):
    """9d-4: units whose gardu the active context may write: own unit; an ULP also its KPs."""
    if ctx.unit.level == 'up3':
        return []
    return child_ids(db, ctx) if ctx.unit.level == 'ulp' else [ctx.id]


def ensure_data_unit(db, ctx, unit_id):
    if unit_id not in data_units(db, ctx):
        raise HTTPException(403, 'Gardu bukan milik unit aktif atau KP di bawahnya')


def ulp_of(db, unit):
    while unit is not None and unit.level == 'kp':
        unit = db.get(OrgUnit, unit.parent_id)
    return unit if unit is not None and unit.level == 'ulp' else None


def master_manager(db, ctx):
    """Global admin, or a verifier granted on the ULP (acting at the ULP or one of its KPs)."""
    if ctx.superadmin:
        return True
    ulp = ulp_of(db, ctx.unit)
    if ulp is None:
        return False
    from ..org_units.models import UserUnitAccess
    return db.query(UserUnitAccess.id).filter_by(user_id=ctx.actor.id, unit_id=ulp.id,
                                                 role='verifier').first() is not None


def require_master_manager(db, ctx):
    if not master_manager(db, ctx):
        raise HTTPException(403, 'Hanya admin global atau verifikator ULP yang dapat mengubah master gardu')


def feeder_units(db, unit_id):
    """A KP gardu may use the feeders of its ULP (feeders are owned by the ULP)."""
    unit = db.get(OrgUnit, unit_id)
    out = [unit_id]
    if unit is not None and unit.level == 'kp' and unit.parent_id:
        out.append(unit.parent_id)
    return out


def family_code_taken(db, unit_id, code, exclude_id=None):
    """Codes stay unique across one ULP and its KPs so a gardu can move without clashing."""
    ulp = ulp_of(db, db.get(OrgUnit, unit_id))
    units = [unit_id]
    if ulp is not None:
        units = [ulp.id] + [r[0] for r in db.query(OrgUnit.id).filter(OrgUnit.parent_id == ulp.id)]
    q = db.query(Substation.id).filter(Substation.unit_id.in_(units), Substation.code == code)
    if exclude_id:
        q = q.filter(Substation.id != exclude_id)
    return q.first() is not None


def ensure_owner(ctx, unit_id):
    if ctx.id != unit_id or ctx.unit.level == 'up3':
        raise HTTPException(403, 'Pilih unit pemilik ULP atau KP')


def require_admin(ctx):
    if not ctx.superadmin:
        raise HTTPException(403, 'Hanya admin global dapat mengubah master')


def require_verifier(ctx):
    if not ctx.superadmin and 'verifier' not in ctx.roles:
        raise HTTPException(403, 'Hanya verifikator atau admin dapat memverifikasi')


def as_number(value, label, positive=False, low=None, high=None):
    if value is None or value == '':
        return None
    try:
        number = Decimal(str(value).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise HTTPException(422, f'{label} harus berupa angka')
    if not number.is_finite() or (positive and number <= 0) or (
            low is not None and number < low) or (high is not None and number > high):
        raise HTTPException(422, f'{label} di luar rentang yang diperbolehkan')
    return number


def check_master(db, unit_id, values):
    if 'code' in values:
        check_code(values['code'])
    if 'name' in values and not str(values['name']).strip():
        raise HTTPException(422, 'Nama gardu wajib diisi')
    if 'power_kva' in values:
        if values['power_kva'] is None: raise HTTPException(422, 'Daya tidak boleh NULL')
        values['power_kva'] = as_number(values['power_kva'], 'Daya kVA', positive=True)
    if 'lat' in values:
        values['lat'] = as_number(values['lat'], 'Latitude', low=-90, high=90)
    if 'lon' in values:
        values['lon'] = as_number(values['lon'], 'Longitude', low=-180, high=180)
    if 'phase' in values and values['phase'] not in (1, 3):
        raise HTTPException(422, 'Fase harus 1 atau 3')
    if 'line_count' in values and values['line_count'] not in range(1, 6):
        raise HTTPException(422, 'Jurusan harus 1 sampai 5')
    if 'year' in values and values['year'] is not None and not 1900 <= values['year'] <= 2200:
        raise HTTPException(422, 'Tahun tidak valid')
    if 'line_labels' in values:
        labels = values['line_labels'] or []
        if not isinstance(labels, list) or len(labels) > 5 or any(
                not isinstance(v, str) or len(v) > 80 for v in labels):
            raise HTTPException(422, 'Label jurusan harus daftar maksimum lima teks')
    feeder_id = values.get('feeder_id')
    if feeder_id is not None:
        feeder = db.get(SubstationFeeder, feeder_id)
        if not feeder or feeder.unit_id not in feeder_units(db, unit_id) or not feeder.active:
            raise HTTPException(422, 'Penyulang harus aktif pada unit pemilik')
    for kind, field in (('ownership', 'ownership'), ('purpose', 'purpose')):
        code = values.get(field)
        if code is not None and not db.query(SubstationChoice).filter_by(
                kind=kind, code=code, active=True).first():
            raise HTTPException(422, f'{field} tidak ada dalam pilihan aktif')
    if 'extra_values' in values:
        extras = values['extra_values'] or {}
        if not isinstance(extras, dict):
            raise HTTPException(422, 'Atribut tambahan harus objek')
        fields = {r.code: r for r in db.query(SubstationField).filter_by(active=True)}
        for code, value in extras.items():
            field = fields.get(code)
            if not field:
                raise HTTPException(422, f'Atribut {code} tidak terdaftar')
            if value is not None and field.kind == 'number':
                as_number(value, code)
            if value is not None and field.kind == 'choice' and value not in (field.options or []):
                raise HTTPException(422, f'Pilihan atribut {code} tidak valid')
            if value is not None and field.kind == 'text' and (not isinstance(value, str) or len(value) > 300):
                raise HTTPException(422, f'Atribut teks {code} tidak valid')
    return values


def page_query(query, page, size):
    if page < 1 or not 1 <= size <= 200:
        raise HTTPException(422, 'Halaman/ukuran halaman tidak valid (maks. 200)')
    total = query.order_by(None).count()
    return {'total': total, 'page': page, 'page_size': size,
            'items': query.offset((page - 1) * size).limit(size).all()}


def master_context():
    """Dependency: write context + master manager check, so 403 comes before body validation."""
    from fastapi import Depends
    from ...db import get_db
    from ..org_units.context import unit_context

    def resolve(ctx=Depends(unit_context('write_data')), db=Depends(get_db)):
        require_master_manager(db, ctx)
        return ctx
    return resolve
