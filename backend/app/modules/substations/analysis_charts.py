"""Read-only chart materialization using the same 9c filtered measurement relation.

No categorization or formula evaluation happens here: 9b matches/values are read.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func, select
from .analysis_data import _session_values, summary
from .analysis_queries import filtered, reference
from .map_service import matching_stations
from .models import SubstationMeasurement
from .models_calc import GarduCalcValue


def charts(db, ctx, opt, station_id=None):
    base = filtered(db, ctx, opt)
    report = summary(db, base)
    selected = matching_stations(db, ctx, opt).subquery()
    ref = reference(db)
    if not ref:
        return {'summary': report, 'scatter': [], 'pareto': [], 'trend': [],
                'reference_code': None, 'scatter_truncated': False}
    values = db.query(selected.c.sid, GarduCalcValue.value).outerjoin(
        GarduCalcValue, (GarduCalcValue.measurement_id == selected.c.mid) &
        (GarduCalcValue.column_id == ref.id)).all()
    pareto = sorted(({'id': sid, 'value': float(value)} for sid, value in values
                     if value is not None), key=lambda r: (-r['value'], r['id']))[:40]
    station_ids = [sid for sid, _ in values]
    points = _session_values(db, station_ids, ref)
    scatter = [{'id': sid, 'sessions': {k: float(v) if v is not None else None
                                      for k, v in sessions.items()}}
               for sid, sessions in points.items()]
    truncated = len(scatter) > 2000
    scatter = scatter[:2000]
    trend = _trend(db, selected, ref.id, station_id)
    return {'summary': report, 'scatter': scatter, 'pareto': pareto, 'trend': trend,
            'reference_code': ref.code, 'reference_unit': ref.unit,
            'scatter_truncated': truncated, 'scatter_total': len(points)}


def _trend(db, selected, column_id, station_id):
    """Last 180 days of stored reference values for selected station(s)."""
    m = SubstationMeasurement
    allowed = select(selected.c.sid).distinct()
    cutoff = datetime.now(ZoneInfo('Asia/Makassar')).date() - timedelta(days=180)
    query = db.query(m.measured_on, m.session,
                     func.avg(GarduCalcValue.value).label('value'))\
        .join(GarduCalcValue, (GarduCalcValue.measurement_id == m.id) &
              (GarduCalcValue.column_id == column_id))\
        .filter(m.substation_id.in_(allowed), m.measured_on >= cutoff)
    if station_id is not None:
        query = query.filter(m.substation_id == station_id)
    return [{'day': day.isoformat(), 'session': session, 'value': float(value)}
            for day, session, value in query.group_by(m.measured_on, m.session)
            .order_by(m.measured_on.desc(), m.session).limit(500).all() if value is not None][::-1]
