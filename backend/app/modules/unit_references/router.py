from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import unit_tree_metrics, status_summary

router = APIRouter(prefix='/api/unit-references', tags=['Unit References'])

@router.get('/metrics')
def metrics(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    return {'unit_id': ctx.id, 'metrics': unit_tree_metrics(db, ctx.id)}

@router.get('/status')
def status(day: date, codes: str = '', ctx: UnitContext = Depends(unit_context('read')),
           db: Session = Depends(get_db)):
    values = [part for part in codes.split(',') if part]
    if not values or len(values) > 45 or any(len(part) > 90 for part in values):
        raise HTTPException(422, 'Pilih 1–45 kode parameter')
    return status_summary(db, ctx.id, values, day)

@router.get('/same-role')
def same_role(role_key: str, ctx: UnitContext = Depends(unit_context('read')),
              db: Session = Depends(get_db)):
    if not role_key or len(role_key) > 60:
        raise HTTPException(422, 'Peran parameter tidak valid')
    return {'role_key': role_key,
            'operands': [m for m in unit_tree_metrics(db, ctx.id)
                         if m['source'] and m['role_key'] == role_key]}
