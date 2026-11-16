"""Read-only coverage matrix, separately scoped from formula completeness."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...db import get_db, User
from ...security import current_user
from ..org_units.context import unit_context
from . import service, export

router = APIRouter(prefix='/api/org-units', tags=['Kelengkapan Unit'],
                   dependencies=[Depends(unit_context('read'))])


def params(start: date, end: date):
    if start > end or (end - start).days >= 62:
        raise HTTPException(422, 'Rentang maksimal 62 hari dan tanggal awal tidak boleh melebihi akhir')
    return start, end


def coverage(id: int, start: date, end: date, db: Session, actor: User):
    start, end = params(start, end)
    items = service.allowed_units(db, actor, id)
    if items is None:
        raise HTTPException(404, 'Unit tidak ditemukan')
    return service.build(db, items, start, end)


@router.get('/{id}/completeness')
def completeness(id: int, start: date = Query(...), end: date = Query(...),
                 db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return coverage(id, start, end, db, actor)


@router.get('/{id}/completeness/export')
def completeness_export(id: int, start: date = Query(...), end: date = Query(...),
                        db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return export.response(coverage(id, start, end, db, actor))
