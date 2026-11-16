"""Per-unit day states and measurement reads; HourRecord remains global."""
from collections import defaultdict
from datetime import date
from fastapi import HTTPException
from ...db import AuditLog, DayState, HourRecord, Metric, Reading, now
from ..org_units.models import UnitDayState, OrgUnit
from ..org_units.repository import home_unit
from ..org_units.context import UnitContext, audit_details
from ..org_units.roles import metric_for_role, SYSTEM_LOAD


def day_state(db, day: date, unit_id: int):
    return db.query(UnitDayState).filter_by(unit_id=unit_id, day=day).first()


def day_status(db, day: date, unit_id: int) -> str:
    row = day_state(db, day, unit_id)
    return row.status if row else 'draft'


def day_readings(db, day: date, unit_id: int):
    rows = (db.query(HourRecord.hour, Metric.code, Reading.value, Reading.source)
            .join(Reading, Reading.hour_id == HourRecord.id)
            .join(Metric, Metric.id == Reading.metric_id)
            .filter(HourRecord.day == day, Metric.unit_id == unit_id)
            .order_by(HourRecord.hour).all())
    values, sources = defaultdict(dict), defaultdict(dict)
    for hour, code, value, source in rows:
        values[hour][code] = float(value)
        sources[hour][code] = source
    return values, sources


def _mirror_legacy(db, row, unit_id: int):
    if unit_id != home_unit(db).id:
        return
    old = db.get(DayState, row.day)
    if old is None:
        old = DayState(day=row.day)
        db.add(old)
    old.status, old.verified_by, old.finalized_by = (
        row.status, row.verified_by, row.finalized_by)
    old.note, old.updated_at = row.note, now()


def transition(db, ctx: UnitContext, day: date, action: str, reason: str):
    """Never commits; caller may combine multiple units atomically."""
    role = 'admin_global' if ctx.superadmin else ctx.role_for('verifier')
    row = day_state(db, day, ctx.id)
    status = row.status if row else 'draft'
    if action == 'verify':
        if status != 'draft':
            raise HTTPException(409, 'Hari tidak berstatus draft')
        values, _ = day_readings(db, day, ctx.id)
        load = metric_for_role(db, ctx.id, SYSTEM_LOAD)
        if ctx.unit.legacy_home:
            if not load:
                raise HTTPException(422, 'Parameter utama belum diatur')
            count = sum(load.code in items for items in values.values())
        else:
            count = sum(bool(items) for items in values.values())
        if not count:
            raise HTTPException(422, 'Belum ada data unit untuk diverifikasi')
        if row is None:
            row = UnitDayState(unit_id=ctx.id, day=day)
            db.add(row)
        row.status, row.verified_by, row.note = 'verified', ctx.actor.id, reason
    elif action == 'finalize':
        if status != 'verified':
            raise HTTPException(409, 'Hari harus diverifikasi dahulu')
        row.status, row.finalized_by, row.note = 'final', ctx.actor.id, reason
    elif action == 'reopen':
        if not ctx.superadmin:
            raise HTTPException(403, 'Hanya admin global boleh membuka kembali hari')
        if status == 'draft':
            raise HTTPException(409, 'Hari belum dikunci')
        row.status, row.note = 'draft', reason
    else:
        raise ValueError('Perubahan status tidak dikenal')
    row.updated_at = now()
    _mirror_legacy(db, row, ctx.id)
    detail = {'unit_id': ctx.id, 'actor_role': role, 'reason': reason}
    if action == 'verify':
        detail['hours'] = count
    if action == 'reopen':
        detail['from'] = status
    db.add(AuditLog(user_id=ctx.actor.id, action=f'day_{action}',
                    target=str(day), detail=detail))
    return {'ok': True, 'status': row.status, **({'hours': count} if action == 'verify' else {})}


def unit_children(db, unit_id: int):
    """ULP and its directly subordinate KPs; no traversal into unrelated ULP."""
    parent = db.get(OrgUnit, unit_id)
    if parent is None or parent.level != 'ulp':
        raise HTTPException(422, 'Tindakan massal hanya untuk ULP dan KP-nya')
    return [parent] + db.query(OrgUnit).filter_by(
        parent_id=unit_id, level='kp', active=True).order_by(OrgUnit.id).all()


def tree_eligibility(db, day: date, unit, action: str):
    """Read-only preflight using the same conditions as transition()."""
    status = day_status(db, day, unit.id)
    if action == 'verify':
        if status != 'draft':
            return False, 'bukan berstatus draft', status
        values, _ = day_readings(db, day, unit.id)
        load = metric_for_role(db, unit.id, SYSTEM_LOAD)
        if unit.legacy_home and load is None:
            return False, 'parameter utama belum diatur', status
        count = sum(load.code in row for row in values.values()) if unit.legacy_home else len(values)
        if not count:
            return False, 'tanpa data', status
    elif action == 'finalize':
        if status != 'verified':
            return False, 'belum diverifikasi' if status == 'draft' else 'bukan berstatus verified', status
    else:
        raise ValueError('Aksi tidak dikenal')
    return True, None, 'verified' if action == 'verify' else 'final'
