"""Pair-wise capacity vs demand history. Missing capacity is never synthesized."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, aliased
from ...db import HourRecord, Metric, Reading, User, get_db
from ..org_units.context import UnitContext, unit_context
from ..org_units.repository import home_unit
from ..org_units.roles import main_pair

router = APIRouter(prefix='/api/monitoring', tags=['Monitoring'])
TZ = ZoneInfo('Asia/Makassar')


def aggregate(db, unit_id: int, start: date, end: date, granularity: str):
    cap_metric, load_metric = main_pair(db, unit_id)
    if not cap_metric or not load_metric:
        return []
    load, cap = aliased(Reading), aliased(Reading)
    grouping = {
        'hour': [HourRecord.day, HourRecord.hour],
        'day': [HourRecord.day],
        'month': [func.extract('year', HourRecord.day), func.extract('month', HourRecord.day)],
        'year': [func.extract('year', HourRecord.day)],
    }[granularity]
    paired_load = case((cap.id.is_not(None), load.value), else_=None)
    query = (db.query(*grouping, func.avg(load.value), func.avg(cap.value),
                      func.avg(paired_load), func.max(load.value), func.min(cap.value),
                      func.count(load.id), func.count(cap.id))
             .join(load, and_(load.hour_id == HourRecord.id, load.metric_id == load_metric.id))
             .outerjoin(cap, and_(cap.hour_id == HourRecord.id, cap.metric_id == cap_metric.id))
             .filter(HourRecord.day >= start, HourRecord.day <= end)
             .group_by(*grouping).order_by(*grouping))
    results = []
    for row in query.all():
        keys = row[:len(grouping)]
        if granularity == 'hour': period = f'{keys[0]} {int(keys[1]):02d}:00'
        elif granularity == 'day': period = str(keys[0])
        elif granularity == 'month': period = f'{int(keys[0])}-{int(keys[1]):02d}'
        else: period = str(int(keys[0]))
        load_avg, cap_avg, paired_avg, load_peak, cap_min, n_load, n_paired = row[len(grouping):]
        results.append({'period': period, 'load_kw': float(load_avg) if load_avg is not None else None,
                        'capacity_kw': float(cap_avg) if cap_avg is not None else None,
                        'paired_load_kw': float(paired_avg) if paired_avg is not None else None,
                        'load_peak_kw': float(load_peak) if load_peak is not None else None,
                        'capacity_min_kw': float(cap_min) if cap_min is not None else None,
                        'load_hours': n_load, 'paired_hours': n_paired})
    return results


@router.get('/capacity-vs-load')
def capacity_vs_load(start: date, end: date, granularity: str = 'hour',
                     ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    if start > end or (end - start).days > 365 * 35:
        raise HTTPException(422, 'Rentang tanggal tidak valid (maks. 35 tahun)')
    if granularity not in ('hour', 'day', 'month', 'year'):
        raise HTTPException(422, 'Granularitas tidak valid')
    if granularity == 'hour' and (end - start).days > 31:
        raise HTTPException(422, 'Grafik per jam maksimal 31 hari')
    if granularity == 'day' and (end - start).days > 366:
        raise HTTPException(422, 'Grafik harian maksimal 366 hari')
    return {'start': str(start), 'end': str(end), 'granularity': granularity,
            'unit': 'kW', 'configured': all(main_pair(db,ctx.id)),
            'data': aggregate(db,ctx.id, start, end, granularity),
            'note': 'Daya mampu berasal dari kolom H rekap (Daya Pasok Pembangkit). Tidak memerlukan input terpisah; titik tanpa data tetap kosong dan agregat dibandingkan pada jam berpasangan.'}
