"""Stage 9e: advice for overloaded gardu. Reading never writes; see advice_followup for tasks."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from . import advice_service as svc

router = APIRouter(prefix='/api/substations/advice', tags=['Gardu Saran'])


@router.get('/{station_id}')
def get_advice(station_id: int, radius_km: float | None = Query(None, gt=0, le=200),
               limit: int = Query(8, ge=1, le=20), measurement_id: int | None = Query(None, ge=1), db: Session = Depends(get_db),
               ctx: UnitContext = Depends(unit_context('read'))):
    return svc.advice(db, ctx, station_id, radius_km, limit, measurement_id)


@router.get('/{station_id}/review')
def get_review(station_id: int, kind: str = Query(pattern='^(swap|move)$'), target_id: int = Query(ge=1),
               line: int | None = Query(None, ge=1, le=5), portion: int | None = Query(None, ge=1, le=100),
               measurement_id: int | None = Query(None, ge=1), db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    return svc.review(db, ctx, station_id, kind, target_id, line, portion, measurement_id)
