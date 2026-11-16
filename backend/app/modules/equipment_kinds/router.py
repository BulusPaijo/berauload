"""Admin-only kind changes; everyone logged in can read the catalog."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import AuditLog, get_db, User
from ...security import current_user, require
from .models import EquipmentKind
from .repository import all_kinds, by_code

router = APIRouter(prefix='/api/equipment-kinds', tags=['Equipment Kinds'])


class NewKind(BaseModel):
    code: str = Field(min_length=2, max_length=35, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(min_length=2, max_length=100)


class KindUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    active: bool


def serialize(item):
    return {'id': item.id, 'code': item.code, 'name': item.name,
            'active': item.active, 'display_order': item.display_order}


def audit(db, user, event, code):
    db.add(AuditLog(user_id=user.id, action=event, target=f'equipment_kind:{code}'))


@router.get('')
def list_kinds(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [serialize(row) for row in all_kinds(db)]


@router.post('', status_code=201)
def create_kind(body: NewKind, user: User = Depends(require('admin')),
                db: Session = Depends(get_db)):
    if by_code(db, body.code):
        raise HTTPException(409, 'Kode jenis peralatan sudah ada')
    kind = EquipmentKind(**body.model_dump(), active=True)
    db.add(kind)
    audit(db, user, 'equipment_kind_create', body.code)
    db.commit()
    return serialize(kind)


@router.put('/{kind_id}')
def update_kind(kind_id: int, body: KindUpdate,
                user: User = Depends(require('admin')), db: Session = Depends(get_db)):
    kind = db.get(EquipmentKind, kind_id)
    if kind is None:
        raise HTTPException(404, 'Jenis peralatan tidak ditemukan')
    kind.name = body.name
    kind.active = body.active
    audit(db, user, 'equipment_kind_update', kind.code)
    db.commit()
    return serialize(kind)
