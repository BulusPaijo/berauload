"""Pure comparison arithmetic and bounded database query for the standard report."""
import calendar
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import HourRecord, Metric, Reading

from ..org_units.roles import metric_for_role, SYSTEM_LOAD


def default_metric(db, unit_id):
    row = metric_for_role(db, unit_id, SYSTEM_LOAD)
    return row.code if row else None
AGGREGATIONS = {'max': 'Maksimum', 'avg': 'Rata-rata', 'min': 'Minimum'}


def validate_selection(db: Session, code: str, aggregation: str, unit_id=None) -> None:
    if aggregation not in AGGREGATIONS:
        raise HTTPException(422, 'Metode harus max, avg, atau min')
    if not isinstance(code, str) or not (1 <= len(code) <= 90):
        raise HTTPException(422, 'Kode parameter tidak valid')
    metric = db.query(Metric).filter_by(code=code, active=True, unit_id=unit_id).first()
    if not metric or code == 'daya_mampu_sistem_kw':
        raise HTTPException(422, 'Parameter tidak aktif atau tidak tersedia')


def growth_pct(before: float | None, after: float | None) -> float | None:
    """No made-up percentage for missing data or zero baseline."""
    if before is None or after is None or before == 0:
        return None
    return round((after / before - 1) * 100, 2)


def summarize_row(maximum, average, minimum, hours):
    return {'peak': float(maximum), 'avg': round(float(average), 2),
            'min': float(minimum), 'hours': int(hours)}


def compare_years(db: Session, year_a: int, year_b: int, metric: str,
                  aggregate: str = 'max') -> dict:
    if not 2020 <= year_a <= 2100 or not 2020 <= year_b <= 2100:
        raise HTTPException(422, 'Tahun tidak valid')
    if aggregate not in AGGREGATIONS:
        raise HTTPException(422, 'Metode harus max, avg, atau min')
    m = db.query(Metric).filter_by(code=metric).first()
    if not m:
        raise HTTPException(404, 'Parameter tidak ditemukan')
    y, mo = func.extract('year', HourRecord.day), func.extract('month', HourRecord.day)
    rows = (db.query(y, mo, func.max(Reading.value), func.avg(Reading.value),
                     func.min(Reading.value), func.count(Reading.id))
            .join(Reading, Reading.hour_id == HourRecord.id)
            .filter(y.in_([year_a, year_b]), Reading.metric_id == m.id)
            .group_by(y, mo).order_by(y, mo).all())
    lookup = {(int(yr), int(month)): summarize_row(pk, av, mn, count)
              for yr, month, pk, av, mn, count in rows}
    results = []
    key = 'peak' if aggregate == 'max' else aggregate
    for month in range(1, 13):
        a, b = lookup.get((year_a, month)), lookup.get((year_b, month))
        complete = bool(a and b and a['hours'] >= calendar.monthrange(year_a, month)[1] * 24
                        and b['hours'] >= calendar.monthrange(year_b, month)[1] * 24)
        aval = a[key] if a else None
        bval = b[key] if b else None
        results.append({'month': month, 'a': a, 'b': b,
                        'value_a': aval, 'value_b': bval,
                        'growth_pct': growth_pct(aval, bval),
                        'peak_growth_pct': growth_pct(a['peak'] if a else None,
                                                     b['peak'] if b else None),
                        'comparable': complete})
    return {'year_a': year_a, 'year_b': year_b, 'metric': metric,
            'metric_name': m.name, 'unit': m.unit, 'aggregation': aggregate,
            'data': results,
            'note': 'Perbandingan parsial diberi status belum comparable; angka sementara bukan YoY resmi.'}
