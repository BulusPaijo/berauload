"""User/system defaults for the standard report parameter selector."""
from ..org_units.context import UnitContext, unit_context
from ..org_units.scoping import scoped_owner
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db
from ...security import current_user, require
from .models import StandardReportSelection
from .service import default_metric, validate_selection

router = APIRouter(prefix='/api/standard-reports', tags=['Standard Report Settings'], dependencies=[Depends(unit_context('read'))])


class SelectionIn(BaseModel):
    metric_code: str = Field(min_length=1, max_length=90)
    aggregation: str = Field(pattern='^(max|avg|min)$')


def resolve(db: Session, user_id: int, unit_id: int):
    system = db.query(StandardReportSelection).filter_by(scope=scoped_owner(db, 'system', unit_id), owner_id=0, unit_id=unit_id).first()
    personal = db.query(StandardReportSelection).filter_by(scope=scoped_owner(db, 'user', unit_id), owner_id=user_id, unit_id=unit_id).first()
    if personal is None:
        personal = db.query(StandardReportSelection).filter_by(
            scope='user', owner_id=user_id, unit_id=unit_id).first()

    def selection(row):
        if row is None:
            return None
        try:
            validate_selection(db, row.metric_code, row.aggregation, unit_id)
        except HTTPException:
            return None
        return {'metric_code': row.metric_code, 'aggregation': row.aggregation}

    default = default_metric(db, unit_id)
    system_value = selection(system) or {'metric_code': default, 'aggregation': 'max'}
    personal_value = selection(personal)
    return {'system': system_value, 'personal': personal_value,
            'effective': personal_value or system_value,
            'source': 'personal' if personal_value else 'system',
            'configured': bool(default)}


def save(db: Session, scope: str, owner_id: int, body: SelectionIn, user_id: int, unit_id: int):
    validate_selection(db, body.metric_code, body.aggregation, unit_id)
    row = db.query(StandardReportSelection).filter_by(scope=scoped_owner(db, scope, unit_id), owner_id=owner_id, unit_id=unit_id).first()
    if row is None:
        row = StandardReportSelection(scope=scoped_owner(db, scope, unit_id), owner_id=owner_id, unit_id=unit_id)
        db.add(row)
    row.metric_code, row.aggregation, row.updated_by = body.metric_code, body.aggregation, user_id
    db.add(AuditLog(user_id=user_id, unit_id=unit_id, action='standard_report_selection', target=f'{scope}:{owner_id}',
                    detail={'metric_code': body.metric_code, 'aggregation': body.aggregation}))
    db.commit()
    return resolve(db, user_id, unit_id)


@router.get('')
def read(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    return resolve(db, u.id, ctx.id)


@router.put('/mine')
def update_mine(body: SelectionIn, u: User = Depends(current_user),
                db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    return save(db, 'user', u.id, body, u.id, ctx.id)


@router.put('/system')
def update_system(body: SelectionIn, u: User = Depends(require('admin')),
                  db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    return save(db, 'system', 0, body, u.id, ctx.id)


@router.delete('/mine')
def reset_mine(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    db.query(StandardReportSelection).filter_by(scope=scoped_owner(db, 'user', ctx.id), owner_id=u.id, unit_id=ctx.id).delete()
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='standard_report_preference_reset', target=str(u.id)))
    db.commit()
    return resolve(db, u.id, ctx.id)
