"""Read-only unit/day completeness; one SQL aggregate over readings."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import and_, case, func, or_
from ...db import HourRecord, Metric, Reading
from ..org_units.models import OrgUnit, UnitDayState
from ..org_units.context import _accessible_rows, _effective_roles

WITA = ZoneInfo('Asia/Makassar')


def clock_now():
    return datetime.now(WITA)


def allowed_units(db, actor, root_id):
    root = db.get(OrgUnit, root_id)
    if not root or not root.active:
        return None
    granted = _accessible_rows(db, actor) if actor.role != 'admin' else []
    if actor.role != 'admin' and not _effective_roles(db, root, granted):
        return None
    units = db.query(OrgUnit).filter(OrgUnit.active.is_(True)).all()
    by_parent = {}
    for unit in units:
        by_parent.setdefault(unit.parent_id, []).append(unit)
    for children in by_parent.values():
        children.sort(key=lambda u: (u.display_order, u.id))
    result, stack = [], [(root, 0)]
    while stack:
        unit, depth = stack.pop()
        if actor.role == 'admin' or _effective_roles(db, unit, granted):
            result.append((unit, depth))
            stack.extend((child, depth + 1) for child in reversed(by_parent.get(unit.id, [])))
    return result


def _hour_counts(db, unit_ids, start, end, today, hour):
    """One grouped query regardless of the number of units/days/cells."""
    load_hour = case((Metric.role_key == 'system.load', HourRecord.hour))
    input_hour = case((and_(Metric.input_mode == 'input', Metric.active.is_(True)), HourRecord.hour))
    rows = db.query(Metric.unit_id, HourRecord.day,
                    func.count(func.distinct(load_hour)),
                    func.count(func.distinct(input_hour))).join(
        Reading, Reading.metric_id == Metric.id).join(
        HourRecord, HourRecord.id == Reading.hour_id).filter(
        Metric.unit_id.in_(unit_ids),
        Reading.value.is_not(None), HourRecord.day >= start,
        HourRecord.day <= end,
        or_(HourRecord.day < today,
            and_(HourRecord.day == today, HourRecord.hour <= hour)),
        or_(Metric.role_key == 'system.load',
            and_(Metric.input_mode == 'input', Metric.active.is_(True)))
    ).group_by(Metric.unit_id, HourRecord.day).all()
    return {(unit_id, day): (load_count, input_count)
            for unit_id, day, load_count, input_count in rows}


def _percent(filled, expected):
    return round(100 * filled / expected, 2) if expected else None


def build(db, units, start: date, end: date, now=None):
    now = now or clock_now()
    today, started_hour = now.date(), now.hour
    data_units = [(u, depth) for u, depth in units if u.level != 'up3']
    ids = [u.id for u, _ in data_units]
    roles = {unit_id for (unit_id,) in db.query(Metric.unit_id).filter(
        Metric.unit_id.in_(ids), Metric.role_key == 'system.load').all()} if ids else set()
    counts = _hour_counts(db, ids, start, end, today, started_hour) if ids else {}
    states = {(unit_id, day): status for unit_id, day, status in db.query(
        UnitDayState.unit_id, UnitDayState.day, UnitDayState.status).filter(
        UnitDayState.unit_id.in_(ids), UnitDayState.day >= start,
        UnitDayState.day <= end).all()} if ids else {}
    dates = [start + timedelta(days=i) for i in range((end-start).days+1)]
    result, total_filled, total_expected, total_final = [], 0, 0, 0
    for unit, depth in data_units:
        basis = 'system.load' if unit.id in roles else 'any_input'
        days, filled_sum, expected_sum, final_days = [], 0, 0, 0
        for day in dates:
            expected = 24 if day < today else (started_hour + 1 if day == today else 0)
            count_pair = counts.get((unit.id, day), (0, 0))
            filled = count_pair[0] if basis == 'system.load' else count_pair[1]
            filled = min(filled, expected)
            status = states.get((unit.id, day), 'draft')
            final_days += int(day <= today and status == 'final')
            filled_sum += filled
            expected_sum += expected
            days.append({'day': day.isoformat(), 'filled_hours': filled,
                         'expected_hours': expected, 'status': status,
                         'future': day > today})
        result.append({'unit_id': unit.id, 'unit_code': unit.code,
                       'unit_name': unit.name, 'level': unit.level,
                       'depth': depth if units[0][0].level != 'up3' else depth - 1,
                       'basis': basis, 'days': days,
                       'summary': {'filled_hours': filled_sum,
                                   'expected_hours': expected_sum,
                                   'percent': _percent(filled_sum, expected_sum),
                                   'final_days': final_days}})
        total_filled += filled_sum
        total_expected += expected_sum
        total_final += final_days
    return {'start': start.isoformat(), 'end': end.isoformat(),
            'dates': [day.isoformat() for day in dates], 'rows': result,
            'summary': {'filled_hours': total_filled,
                        'expected_hours': total_expected,
                        'percent': _percent(total_filled, total_expected),
                        'final_days': total_final}}
