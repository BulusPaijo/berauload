"""Stage 9d-3 monitoring: coverage per unit and stations not measured within N days (counts only)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import Integer, and_, func
from ..org_units.models import OrgUnit
from .common import child_ids
from .models import Substation, SubstationFeeder, SubstationMeasurement
from .models_calc import GarduCalcSettings


def today():
    return datetime.now(ZoneInfo('Asia/Makassar')).date()


def stale_days(db):
    s = db.get(GarduCalcSettings, 1)
    return s.stale_days if s else 180


def last_measured(db, allowed):
    m = SubstationMeasurement
    return db.query(m.substation_id.label('sid'), func.max(m.measured_on).label('last')).filter(
        m.unit_id.in_(allowed)).group_by(m.substation_id).subquery()


def coverage(db, ctx, start: date, end: date):
    allowed = child_ids(db, ctx)
    last = last_measured(db, allowed)
    s, m = Substation, SubstationMeasurement
    limit = today() - timedelta(days=stale_days(db))
    in_range = db.query(m.substation_id).filter(m.unit_id.in_(allowed),
                                                m.measured_on.between(start, end)).distinct().subquery()
    rows = db.query(s.unit_id, func.count(s.id),
                    func.count(in_range.c.substation_id),
                    func.sum(func.cast(last.c.last.is_(None), Integer)),
                    func.sum(func.cast(and_(last.c.last.isnot(None), last.c.last < limit), Integer)))\
        .outerjoin(in_range, in_range.c.substation_id == s.id)\
        .outerjoin(last, last.c.sid == s.id)\
        .filter(s.unit_id.in_(allowed), s.active.is_(True)).group_by(s.unit_id).all()
    units = {u.id: u for u in db.query(OrgUnit).filter(OrgUnit.id.in_(allowed))}
    items = []
    for unit_id, total, measured, never, stale in rows:
        u = units.get(unit_id)
        items.append({'unit_id': unit_id, 'unit': u.name if u else str(unit_id), 'level': u.level if u else '',
                      'total': total, 'measured': measured, 'never': int(never or 0), 'stale': int(stale or 0),
                      'percent': round(measured * 100 / total, 1) if total else None})
    items.sort(key=lambda r: r['unit'])
    tot = {k: sum(r[k] for r in items) for k in ('total', 'measured', 'never', 'stale')}
    tot['percent'] = round(tot['measured'] * 100 / tot['total'], 1) if tot['total'] else None
    return {'start': start.isoformat(), 'end': end.isoformat(), 'stale_days': stale_days(db),
            'items': items, 'total': tot}


def unmeasured(db, ctx, days: int, feeder_id=None, text='', page=1, page_size=50):
    allowed = child_ids(db, ctx)
    last = last_measured(db, allowed)
    s = Substation
    limit = today() - timedelta(days=days)
    q = db.query(s, last.c.last).outerjoin(last, last.c.sid == s.id).filter(
        s.unit_id.in_(allowed), s.active.is_(True), (last.c.last.is_(None)) | (last.c.last < limit))
    if feeder_id:
        q = q.filter(s.feeder_id == feeder_id)
    if text:
        q = q.filter(s.code.ilike(f'%{text}%') | s.name.ilike(f'%{text}%'))
    total = q.count()
    rows = q.order_by(last.c.last.isnot(None), last.c.last, s.code).offset((page - 1) * page_size).limit(page_size).all()
    feeders = {f.id: f.name for f in db.query(SubstationFeeder.id, SubstationFeeder.name)}
    now = today()
    return {'days': days, 'total': total, 'items': [{
        'id': st.id, 'code': st.code, 'name': st.name, 'unit_id': st.unit_id, 'feeder': feeders.get(st.feeder_id),
        'power_kva': float(st.power_kva), 'line_count': st.line_count,
        'last_measured_on': d.isoformat() if d else None, 'age_days': (now - d).days if d else None} for st, d in rows]}
