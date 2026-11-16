"""Multi-metric time-series query. Matches existing /api/analytics aggregations."""
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import HourRecord, Reading, Metric


def _grouping(granularity):
    if granularity == 'hour':
        return [HourRecord.day, HourRecord.hour]
    if granularity == 'day':
        return [HourRecord.day]
    if granularity == 'month':
        return [func.extract('year', HourRecord.day), func.extract('month', HourRecord.day)]
    return [func.extract('year', HourRecord.day)]


def _period(keys, granularity):
    if granularity == 'hour':
        return f'{keys[0]} {int(keys[1]):02d}:00'
    if granularity == 'day':
        return str(keys[0])
    if granularity == 'month':
        return f'{int(keys[0])}-{int(keys[1]):02d}'
    return str(int(keys[0]))


def query_batch(db: Session, ids: dict[str, int], granularity: str,
                start: date, end: date):
    """Single grouped query instead of N independent analytics queries."""
    groups = _grouping(granularity)
    rows = (db.query(Metric.code, *groups, func.min(Reading.value),
                     func.max(Reading.value), func.avg(Reading.value),
                     func.count(Reading.id))
            .join(Reading, Reading.metric_id == Metric.id)
            .join(HourRecord, HourRecord.id == Reading.hour_id)
            .filter(Metric.id.in_(list(ids.values())),
                    HourRecord.day >= start, HourRecord.day <= end)
            .group_by(Metric.code, *groups).order_by(Metric.code, *groups))
    data = {code: [] for code in ids}
    n = len(groups)
    for row in rows:
        code = row[0]
        low, peak, avg, count = row[n + 1:]
        data[code].append({'period': _period(row[1:n+1], granularity),
                           'min': float(low), 'peak': float(peak),
                           'avg': round(float(avg), 3), 'count': count})
    return data
