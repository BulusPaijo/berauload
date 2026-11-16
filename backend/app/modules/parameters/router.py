"""Stage 3 modular route extraction; legacy URL and behavior preserved."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import Metric, AuditLog, User, get_db
from ...security import current_user, require
from ..org_units.repository import role_conflict
from ..org_units.context import UnitContext, unit_context
from ..org_units.service import validate_role_key, OrgError
from ..org_units.usage import metric_usage
router = APIRouter(prefix='/api', tags=['Parameters'])

class NameUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    active: bool = True

class MetricUpdate(NameUpdate):
    role_key: str | None = None
    confirm_disable: bool = False

def audit(db,u,action,target,detail):
    db.add(AuditLog(user_id=u.id,action=action,target=target,detail=detail))

@router.get('/metrics/{id}/usage')
def get_metric_usage(id:int,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    metric=db.get(Metric,id)
    if not metric or metric.unit_id!=ctx.id:raise HTTPException(404,'Parameter tidak ditemukan')
    return {'metric_code':metric.code,'usage':metric_usage(db,metric)}

@router.put('/metrics/{id}')
def update_metric(id:int,body:MetricUpdate,u:User=Depends(require('admin')),ctx:UnitContext=Depends(unit_context('configure')),db:Session=Depends(get_db)):
    m=db.get(Metric,id)
    if not m or m.unit_id!=ctx.id: raise HTTPException(404,'Parameter tidak ditemukan')
    if 'role_key' in body.model_fields_set:
        try:
            role = validate_role_key(body.role_key)
        except OrgError as exc:
            raise HTTPException(422, str(exc)) from exc
        if role and role_conflict(db, m.unit_id, role, except_id=m.id):
            raise HTTPException(409, 'Kunci peran sudah digunakan pada unit ini')
        m.role_key = role
    if m.active and not body.active:
        used = metric_usage(db,m)
        if used and not body.confirm_disable:
            raise HTTPException(409, {'message':'Parameter masih dipakai; konfirmasi diperlukan', 'usage':used[:200]})
    m.name,m.active=body.name,body.active
    audit(db,u,'metric_update',m.code,{'unit_id':ctx.id,'actor_role':'admin_global',**body.model_dump()});db.commit()
    return {'ok':True}

