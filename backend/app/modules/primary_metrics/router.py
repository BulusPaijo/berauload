"""Global-admin configuration of main readings for the current home unit."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...db import Metric, AuditLog, User, get_db
from ...security import current_user, require
from ..org_units.context import UnitContext, unit_context
from ..org_units.roles import SYSTEM_CAPACITY, SYSTEM_LOAD, MAIN_ROLES, main_pair, role_codes

router = APIRouter(prefix='/api/primary-metrics', tags=['Primary Metrics'])


class MainMetricSelection(BaseModel):
    load_code: str | None
    capacity_code: str | None


def serialize(db: Session, unit_id: int):
    cap, load = main_pair(db, unit_id)
    return {'unit_id': unit_id, 'configured': bool(cap and load),
            'load_code': load.code if load else None,
            'capacity_code': cap.code if cap else None,
            'roles': role_codes(db, unit_id)}


@router.get('')
def read(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    return serialize(db, ctx.id)


@router.put('')
def update(body: MainMetricSelection, u: User = Depends(require('admin')),
           ctx: UnitContext = Depends(unit_context('configure')),
           db: Session = Depends(get_db)):
    unit_id = ctx.id
    values = (body.capacity_code, body.load_code)
    if values[0] is not None and values[0] == values[1]:
        raise HTTPException(422, 'Daya mampu dan beban harus dua parameter berbeda')
    chosen = {}
    for role, code in zip((SYSTEM_CAPACITY, SYSTEM_LOAD), values):
        if code is None:
            continue
        metric = db.query(Metric).filter_by(code=code, unit_id=unit_id, active=True).first()
        if not metric:
            raise HTTPException(422, f'Parameter {code} tidak aktif atau bukan milik unit')
        if metric.role_key not in (None, *MAIN_ROLES):
            raise HTTPException(409, f'Parameter {code} sudah mempunyai peran {metric.role_key}')
        chosen[role] = metric
    existing = db.query(Metric).filter(
        Metric.unit_id == unit_id, Metric.role_key.in_(MAIN_ROLES)).all()
    before = {m.role_key: m.code for m in existing}
    for metric in existing:
        metric.role_key = None
    db.flush()  # release partial unique (unit_id, role_key) before reassignment
    for role, metric in chosen.items():
        metric.role_key = role
    db.add(AuditLog(user_id=u.id, action='main_metric_roles_update',
                    target=str(unit_id), detail={'unit_id':unit_id,'actor_role':'admin_global','before': before, 'after': body.model_dump()}))
    db.commit()
    return serialize(db, unit_id)
