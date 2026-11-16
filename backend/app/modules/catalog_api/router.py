"""Stage 4a: unit-scoped catalogue and global-admin configuration."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import Asset, Metric, AuditLog, User, get_db
from ...security import require
from ..units.models import UnitDefinition
from ..equipment_kinds.repository import by_code as kind_by_code
from ..equipment_kinds.service import require_active_kind
from ..input_forms.models import InputFormTab, InputFormPlacement, InputFormRevision
from ..org_units.context import UnitContext, unit_context
from ..org_units.roles import SYSTEM_CAPACITY, role_codes
router = APIRouter(prefix='/api',tags=['Catalog'])
def audit(db,u,action,target,detail=None):
    db.add(AuditLog(user_id=u.id,action=action,target=target,detail=detail or {}))

@router.get('/catalog')
def catalog(ctx:UnitContext=Depends(unit_context('read')), db:Session=Depends(get_db)):
    assets=db.query(Asset).filter_by(unit_id=ctx.id).order_by(Asset.kind,Asset.name).all()
    metrics=db.query(Metric).filter_by(unit_id=ctx.id).order_by(Metric.display_order).all()
    home_id = ctx.id
    return {'roles':role_codes(db,home_id), 'assets':[{'id':a.id,'code':a.code,'name':a.name,'kind':a.kind,'active':a.active,'unit_id':a.unit_id} for a in assets],
            'metrics':[{'id':m.id,'code':m.code,'name':(
                'Daya Mampu Sistem (kolom H rekap)' if m.role_key==SYSTEM_CAPACITY and m.name=='Daya Pasok Pembangkit'
                else 'Daya Mampu Manual (Legacy V1.1; tidak untuk grafik)' if m.code=='daya_mampu_sistem_kw' and m.name=='Daya Mampu Sistem'
                else m.name), 'unit':m.unit,'group':m.group_name,
                        'mode':m.input_mode,'active':m.active,'asset_id':m.asset_id,
                        'unit_id':m.unit_id,'role_key':m.role_key} for m in metrics]}

class NameUpdate(BaseModel):
    name:str=Field(min_length=2,max_length=180)
    active:bool=True

@router.put('/assets/{id}')
def update_asset(id:int,body:NameUpdate,u:User=Depends(require('admin')),
                 ctx:UnitContext=Depends(unit_context('configure')),
                 db:Session=Depends(get_db)):
    a=db.get(Asset,id)
    if not a or a.unit_id!=ctx.id: raise HTTPException(404,'Peralatan tidak ditemukan')
    a.name,a.active=body.name,body.active
    audit(db,u,'asset_update',a.code,{'unit_id':ctx.id,'actor_role':'admin_global',**body.model_dump()});db.commit()
    return {'ok':True}

class CreateAsset(BaseModel):
    code:str=Field(min_length=2,max_length=80,pattern=r'^[a-z][a-z0-9_]*$')
    name:str=Field(min_length=2,max_length=180)
    kind:str=Field(min_length=2,max_length=35)

@router.post('/assets')
def create_asset(body:CreateAsset,u:User=Depends(require('admin')),
                 ctx:UnitContext=Depends(unit_context('configure')),
                 db:Session=Depends(get_db)):
    if ctx.unit.level=='up3':raise HTTPException(422,'UP3 tidak memiliki peralatan')
    if db.query(Asset.id).filter_by(code=body.code).first():raise HTTPException(409,'Kode peralatan sudah digunakan')
    require_active_kind(kind_by_code(db, body.kind))
    row=Asset(**body.model_dump(),unit_id=ctx.id);db.add(row)
    audit(db,u,'asset_create',body.code,{'unit_id':ctx.id,'actor_role':'admin_global'});db.commit()
    return {'ok':True,'id':row.id}

class CreateMetric(BaseModel):
    code:str=Field(min_length=2,max_length=90,pattern=r'^[a-z][a-z0-9_]*$')
    name:str=Field(min_length=2,max_length=180)
    unit:str=Field(min_length=1,max_length=12)
    group_name:str=Field(min_length=2,max_length=35)
    asset_id:int|None=None
    input_tab_code:str|None=None

@router.post('/metrics')
def create_metric(body:CreateMetric,u:User=Depends(require('admin')),
                  ctx:UnitContext=Depends(unit_context('configure')),
                  db:Session=Depends(get_db)):
    if ctx.unit.level=='up3':raise HTTPException(422,'UP3 tidak memiliki parameter input')
    if db.query(Metric.id).filter_by(code=body.code).first():raise HTTPException(409,'Kode parameter sudah digunakan')
    if body.group_name not in ('PEMBANGKIT','KUALITAS','FEEDER','REKAP','REKAP_LAIN'):
        raise HTTPException(422,'Kelompok parameter tidak valid')
    if body.asset_id is not None and not db.query(Asset.id).filter_by(id=body.asset_id,unit_id=ctx.id).first():
        raise HTTPException(422,'Peralatan tidak ditemukan')
    unit_row = db.query(UnitDefinition).filter_by(code=body.unit, active=True).first()
    if unit_row is None:raise HTTPException(422,'Satuan belum terdaftar atau tidak aktif')
    highest=db.query(func.max(Metric.display_order)).scalar() or 0
    if body.input_tab_code is not None:
        chosen=db.query(InputFormTab).filter_by(code=body.input_tab_code,active=True,unit_id=ctx.id).first()
        if chosen is None:raise HTTPException(422,'Tab formulir tidak aktif atau tidak ditemukan')
    row=Metric(**body.model_dump(exclude={'input_tab_code'}),input_mode='input',
               display_order=highest+1,active=True,unit_id=ctx.id)
    db.add(row)
    if body.input_tab_code is not None:
        db.add(InputFormPlacement(unit_id=ctx.id, metric_code=body.code,
               tab_code=body.input_tab_code,display_order=highest+1,visible=True))
    rev=db.query(InputFormRevision).filter_by(unit_id=ctx.id).first()
    if rev:rev.version+=1
    audit(db,u,'metric_create',body.code,{'unit_id':ctx.id,'actor_role':'admin_global'});db.commit()
    return {'ok':True,'id':row.id}

