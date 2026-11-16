"""Existing user admin routes moved from main without changing permissions."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal
from sqlalchemy.orm import Session
from ...db import User, LoginSession, AuditLog, get_db
from ...security import hash_password, require
from ..org_units.models import OrgUnit, UserUnitAccess
from ..org_units.repository import attach_new_user
router = APIRouter(prefix='/api', tags=['Users'])

def audit(db,u,action,target=None,detail=None):
    db.add(AuditLog(user_id=u.id,action=action,target=target,detail=detail or {}))

class UnitGrant(BaseModel):
    model_config = ConfigDict(extra='forbid')
    unit_id: int = Field(gt=0)
    role: Literal['operator', 'verifier', 'management']


class NewUser(BaseModel):
    username:str=Field(min_length=3,max_length=70,pattern=r'^[a-zA-Z0-9_.-]+$')
    display_name:str=Field(min_length=2,max_length=150)
    password:str=Field(min_length=16,max_length=200)
    role:str
    accesses:list[UnitGrant]=Field(default_factory=list, max_length=100)
    @field_validator('role')
    @classmethod
    def valid_role(cls,x):
        if x not in ('operator','verifier','management','admin'): raise ValueError('Role tidak valid')
        return x

@router.get('/users')
def users(u:User=Depends(require('admin')),db:Session=Depends(get_db)):
    return [{'id':x.id,'username':x.username,'name':x.display_name,'role':x.role,'active':x.active} for x in db.query(User).order_by(User.username)]

@router.post('/users')
def new_user(body:NewUser,u:User=Depends(require('admin')),db:Session=Depends(get_db)):
    if db.query(User.id).filter_by(username=body.username).first(): raise HTTPException(409,'Username sudah ada')
    row=User(username=body.username,display_name=body.display_name,
             password_hash=hash_password(body.password),role=body.role)
    grants = [grant.model_dump() for grant in body.accesses]
    if body.role != 'admin' and not grants:
        raise HTTPException(422, 'Pengguna non-admin wajib memiliki akses unit eksplisit')
    if body.role == 'admin' and grants:
        raise HTTPException(422, 'Admin menggunakan peran global, bukan akses unit')
    ids = [g.get('unit_id') for g in grants]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, 'Akses unit duplikat')
    for grant in grants:
        unit = db.get(OrgUnit, grant['unit_id'])
        if not unit or not unit.active or grant.get('role') not in ('operator','verifier','management'):
            raise HTTPException(422, 'Unit tidak aktif atau role akses tidak valid')
        if unit.level == 'up3' and grant['role'] != 'management':
            raise HTTPException(422, 'Pengguna UP3 selain admin hanya dapat melihat')
    db.add(row)
    db.flush()
    if body.role == 'admin':
        attach_new_user(db, row)
    db.add_all(UserUnitAccess(user_id=row.id, unit_id=g['unit_id'], role=g['role']) for g in grants)
    audit(db,u,'user_create',body.username,{'role':body.role, 'accesses':grants})
    db.commit()
    return {'ok':True,'id':row.id}

class UserActive(BaseModel):
    active:bool

@router.put('/users/{id}/active')
def set_user_active(id:int,body:UserActive,u:User=Depends(require('admin')),db:Session=Depends(get_db)):
    target=db.get(User,id)
    if not target:raise HTTPException(404,'Pengguna tidak ditemukan')
    if not body.active and target.id==u.id:raise HTTPException(422,'Tidak boleh menonaktifkan akun sendiri')
    if not body.active and target.role=='admin':
        n=db.query(User).filter_by(role='admin',active=True).count()
        if n<2:raise HTTPException(422,'Admin aktif terakhir tidak boleh dinonaktifkan')
    target.active=body.active
    if not body.active:db.query(LoginSession).filter_by(user_id=id).delete()
    audit(db,u,'user_status',target.username,{'active':body.active});db.commit()
    return {'ok':True}

class ResetPassword(BaseModel):
    password:str=Field(min_length=16,max_length=200)

@router.post('/users/{id}/reset-password')
def reset_password(id:int,body:ResetPassword,u:User=Depends(require('admin')),db:Session=Depends(get_db)):
    target=db.get(User,id)
    if not target: raise HTTPException(404,'Pengguna tidak ditemukan')
    target.password_hash=hash_password(body.password)
    db.query(LoginSession).filter_by(user_id=id).delete()
    audit(db,u,'password_reset',target.username);db.commit()
    return {'ok':True}

