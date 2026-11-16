"""Read-only batching for dashboard charts. No writes to operational data."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...db import Metric, User, get_db
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import validate_codes, status_summary
from .cache import get_or_compute
from .service import query_batch

router = APIRouter(prefix='/api/performance', tags=['Performance'])


@router.get('/series')
def batch_series(start: date, end: date, granularity: str = 'day',
                 codes: str = Query(min_length=2, max_length=370),
                 ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    selected = codes.split(',')
    if not 1 <= len(selected) <= 4 or len(set(selected)) != len(selected):
        raise HTTPException(422, 'Pilih 1–4 parameter berbeda')
    if any(not code or len(code) > 90 for code in selected):
        raise HTTPException(422, 'Kode parameter tidak valid')
    if end < start or (end-start).days > 365*35:
        raise HTTPException(422, 'Rentang tanggal tidak valid')
    if granularity not in {'hour', 'day', 'month', 'year'}:
        raise HTTPException(422, 'Resolusi tidak valid')
    if granularity == 'hour' and (end-start).days > 31:
        raise HTTPException(422, 'Resolusi jam maksimal 31 hari')
    if granularity == 'day' and (end-start).days > 366:
        raise HTTPException(422, 'Resolusi harian maksimal 366 hari')
    by_code = validate_codes(db, ctx.id, selected)
    ids = {code: by_code[code].id for code in selected}
    key = (ctx.id, start.isoformat(), end.isoformat(), granularity, tuple(sorted(ids.items())))
    data = get_or_compute(key, lambda: query_batch(db, ids, granularity, start, end))
    return {'data': data, 'source_status': status_summary(db, ctx.id, selected, end),
            'units': {code: by_code[code].unit for code in selected},
            'start': str(start), 'end': str(end), 'granularity': granularity}
