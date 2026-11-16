"""Recalculate downstream formulas inside the source's SQL transaction.

Only affected explicit formulas are evaluated. Locked ULP results are never
rewritten; a source-change flag is retained for verifier review. UP3 has no
status lock and always uses the currently committed source snapshot.
"""
from decimal import Decimal
from ...db import AuditLog, HourRecord, Metric, Reading
from ..formulas.engine import parse_formula
from ..formulas.service import active_plan, calculate_custom
from ..org_units.models import OrgUnit
from ..records.service import day_status
from .models import UnitSourceChange


def _hour_values(db, hour_id, codes):
    if not codes:
        return {}
    rows = db.query(Metric.code, Reading.value).join(
        Reading, Reading.metric_id == Metric.id).filter(
        Reading.hour_id == hour_id, Metric.code.in_(codes)).all()
    return {code: float(value) for code, value in rows}


def _set_computed(db, hour_id, metric, value):
    row = db.query(Reading).filter_by(hour_id=hour_id, metric_id=metric.id).first()
    new = Decimal(str(value)) if value is not None else None
    if row is None and new is None:
        return False
    if row is not None and new == row.value:
        return False
    if new is None:
        db.delete(row)
    elif row:
        row.value, row.source = new, 'computed'
    else:
        db.add(Reading(hour_id=hour_id, metric_id=metric.id,
                       value=new, source='computed'))
    return True


def _mark_locked(db, target, source_id, day, hour):
    if not db.query(UnitSourceChange.id).filter_by(
            unit_id=target.id, source_unit_id=source_id,
            day=day, hour=hour).first():
        db.add(UnitSourceChange(unit_id=target.id, source_unit_id=source_id,
                                day=day, hour=hour))
        db.add(AuditLog(unit_id=target.id, action='source_changed_after_final',
                        target=f'{day} {hour:02d}:00', detail={
                            'unit_id': target.id, 'source_unit_id': source_id,
                            'status': day_status(db, day, target.id)}))


def recalculate(db, day, hour, source_id, changed_codes):
    """Call after source writes but before commit. Safe to repeat in a transaction."""
    record = db.query(HourRecord).filter_by(day=day, hour=hour).first()
    if record is None or not changed_codes:
        return
    db.flush()
    # Ancestors are discovered from the source's parent chain, not descendants.
    cursor = db.get(OrgUnit, source_id)
    owners = {source_id}
    while cursor is not None and cursor.parent_id is not None:
        owners.add(cursor.parent_id)
        cursor = db.get(OrgUnit, cursor.parent_id)
    dirty = set(changed_codes)
    for definition, metric in active_plan(db):
        if metric.unit_id not in owners:
            continue
        refs = parse_formula(definition.expression)[1]
        if not refs.intersection(dirty):
            continue
        target = db.get(OrgUnit, metric.unit_id)
        if target.level != 'up3' and day_status(db, day, target.id) != 'draft':
            if target.id != source_id:
                _mark_locked(db, target, source_id, day, hour)
            continue
        inputs = _hour_values(db, record.id, refs)
        computed, _ = calculate_custom(db, inputs, plan=[(definition, metric)])
        if _set_computed(db, record.id, metric, computed.get(metric.code)):
            dirty.add(metric.code)
            db.flush()


def refresh_reopened_day(db, unit_id, day):
    """Re-evaluate flagged hours after an admin explicitly reopens a parent day."""
    changes = db.query(UnitSourceChange).filter_by(unit_id=unit_id, day=day).all()
    for item in changes:
        source_codes = {m.code for m in db.query(Metric).filter_by(
            unit_id=item.source_unit_id).all()}
        recalculate(db, day, item.hour, item.source_unit_id, source_codes)
        db.delete(item)
    return len(changes)
