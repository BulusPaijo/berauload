"""REST interface for admin defaults and user chart preferences."""
from ..org_units.context import UnitContext, unit_context
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db
from ...security import current_user, require
from .repository import delete_personal, get_settings, save_settings
from .service import default_codes, MAX_SERIES, validate_codes

router = APIRouter(prefix='/api/dashboard-charts', tags=['Dashboard Chart Settings'], dependencies=[Depends(unit_context('read'))])


class ChartSelection(BaseModel):
    metric_codes: list[str] = Field(min_length=1, max_length=MAX_SERIES)


def describe(db: Session, user_id: int, unit_id: int):
    system = get_settings(db, 'system', 0, unit_id)
    personal = get_settings(db, 'user', user_id, unit_id)
    defaults = default_codes(db, unit_id)
    system_codes = list(system.metric_codes) if system else defaults
    # Settings might reference subsequently deactivated parameters: fall back safely.
    try:
        validate_codes(db, system_codes, unit_id)
    except HTTPException:
        system_codes = defaults
    user_codes = list(personal.metric_codes) if personal else None
    if user_codes is not None:
        try:
            validate_codes(db, user_codes, unit_id)
        except HTTPException:
            user_codes = None
    return {
        'system': system_codes,
        'personal': user_codes,
        'effective': user_codes if user_codes is not None else system_codes,
        'source': 'personal' if user_codes is not None else 'system',
        'max_series': MAX_SERIES,
        'configured': len(defaults) == 2,
    }


@router.get('')
def read_selection(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    return describe(db, u.id, ctx.id)


@router.put('/system')
def update_system(body: ChartSelection, u: User = Depends(require('admin')),
                  db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    codes = validate_codes(db, body.metric_codes, ctx.id)
    save_settings(db, 'system', 0, codes, u.id, ctx.id)
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='chart_default_update', target='system',
                    detail={'metric_codes': codes}))
    db.commit()
    return describe(db, u.id, ctx.id)


@router.put('/mine')
def update_personal(body: ChartSelection, u: User = Depends(current_user),
                    db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    codes = validate_codes(db, body.metric_codes, ctx.id)
    save_settings(db, 'user', u.id, codes, u.id, ctx.id)
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='chart_preference_update', target=str(u.id),
                    detail={'metric_codes': codes}))
    db.commit()
    return describe(db, u.id, ctx.id)


@router.delete('/mine')
def reset_personal(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    delete_personal(db, u.id, ctx.id)
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='chart_preference_reset', target=str(u.id)))
    db.commit()
    return describe(db, u.id, ctx.id)
