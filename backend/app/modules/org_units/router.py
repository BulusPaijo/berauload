"""Admin configuration only. Global permissions remain unchanged in Stage 1."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db
from ...security import current_user, require
from .models import OrgUnit, UserUnitAccess
from .repository import access_rows, home_unit, unit_dict, units
from .context import _accessible_rows, _effective_roles
from ..input_forms.bootstrap import seed_unit_tabs
from .service import (OrgError, validate_code, validate_creation,
                      validate_deactivation)

router = APIRouter(prefix='/api/org-units', tags=['Struktur Organisasi'])
ROLES = ('operator', 'verifier', 'management')

class CreateUnit(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=180)
    level: str
    parent_id: int | None = None
    display_order: int = Field(default=0, ge=0, le=100000)

class UpdateUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=180)
    display_order: int = Field(ge=0, le=100000)

class UnitStatus(BaseModel):
    active: bool

class AccessItem(BaseModel):
    user_id: int
    role: str

class SetAccess(BaseModel):
    entries: list[AccessItem] = Field(max_length=10000)


def _audit(db, user, action, target, detail):
    db.add(AuditLog(user_id=user.id, action=action,
                    target=f'unit:{target}', detail=detail))

def _unit(db, unit_id):
    row = db.get(OrgUnit, unit_id)
    if row is None:
        raise HTTPException(404, 'Unit tidak ditemukan')
    return row

def _tree(rows):
    nodes = {u.id: {**unit_dict(u), 'children': []} for u in rows}
    roots = []
    for u in rows:
        if u.parent_id is None or u.parent_id not in nodes:
            roots.append(nodes[u.id])
        elif u.parent_id in nodes:
            nodes[u.parent_id]['children'].append(nodes[u.id])
    return roots

@router.get('')
def list_units(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=units(db)
    if user.role!='admin':
        access=_accessible_rows(db,user)
        rows=[unit for unit in rows if unit.active and _effective_roles(db,unit,access)]
    result = []
    for unit in rows:
        item = {**unit_dict(unit),
                'roles': ['admin_global'] if user.role == 'admin' else sorted(_effective_roles(db, unit, access))}
        result.append(item)
    return _tree_with_roles(result)


def _tree_with_roles(items):
    nodes = {row['id']: {**row, 'children': []} for row in items}
    roots = []
    for row in items:
        if row['parent_id'] not in nodes:
            roots.append(nodes[row['id']])
        else:
            nodes[row['parent_id']]['children'].append(nodes[row['id']])
    return roots

@router.get('/selectable')
def selectable_units(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # The administration tree may include archived units; the operational picker cannot.
    rows = [unit for unit in units(db) if unit.active]
    access = _accessible_rows(db, user) if user.role != 'admin' else []
    if user.role != 'admin':
        rows = [unit for unit in rows if _effective_roles(db, unit, access)]
    return _tree_with_roles([{**unit_dict(unit),
             'roles': ['admin_global'] if user.role == 'admin'
                      else sorted(_effective_roles(db, unit, access))}
            for unit in rows])


@router.post('', status_code=201)
def create_unit(body: CreateUnit, user: User = Depends(require('admin')),
                db: Session = Depends(get_db)):
    try:
        validate_code(body.code)
        validate_creation(body.level, unit_dict(_unit(db, body.parent_id)) if body.parent_id else None,
                            [unit_dict(u) for u in units(db)])
        if body.level == 'up3':
            raise OrgError('UP3 kedua tidak diizinkan')
        if db.query(OrgUnit.id).filter_by(code=body.code).first():
            raise HTTPException(409, 'Kode unit sudah digunakan')
        row = OrgUnit(**body.model_dump(), active=True)
        db.add(row)
        db.flush()
        seed_unit_tabs(db, row)
        _audit(db, user, 'org_unit_create', row.code, {'level': row.level, 'parent_id': row.parent_id})
        db.commit()
    except OrgError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode unit sudah terdaftar') from exc
    return unit_dict(row)

@router.put('/{id}')
def update_unit(id: int, body: UpdateUnit, user: User = Depends(require('admin')),
                db: Session = Depends(get_db)):
    row = _unit(db, id)
    before = {'name': row.name, 'display_order': row.display_order}
    row.name, row.display_order = body.name, body.display_order
    _audit(db, user, 'org_unit_update', row.code, {'before': before, 'after': body.model_dump()})
    db.commit()
    return unit_dict(row)

@router.put('/{id}/status')
def status_unit(id: int, body: UnitStatus, user: User = Depends(require('admin')),
                db: Session = Depends(get_db)):
    row = _unit(db, id)
    if not body.active:
        try:
            validate_deactivation(unit_dict(row), [unit_dict(u) for u in units(db)])
        except OrgError as exc:
            raise HTTPException(422, str(exc)) from exc
    elif row.parent_id is not None and not _unit(db, row.parent_id).active:
        raise HTTPException(422, 'Aktifkan unit induk terlebih dahulu')
    row.active = body.active
    _audit(db, user, 'org_unit_status', row.code, {'active': body.active})
    db.commit()
    return unit_dict(row)

@router.get('/{id}/access')
def get_access(id: int, user: User = Depends(require('admin')),
               db: Session = Depends(get_db)):
    _unit(db, id)
    return [{'user_id': r.user_id, 'unit_id': r.unit_id, 'role': r.role}
            for r in access_rows(db, id)]

@router.put('/{id}/access')
def set_access(id: int, body: SetAccess, user: User = Depends(require('admin')),
               db: Session = Depends(get_db)):
    target_unit = _unit(db, id)
    if not target_unit.active:
        raise HTTPException(422, 'Unit nonaktif tidak dapat menerima akses')
    ids = [entry.user_id for entry in body.entries]
    if len(ids) != len(set(ids)) or any(entry.role not in ROLES for entry in body.entries):
        raise HTTPException(422, 'Akses duplikat atau role tidak valid')
    if len(ids) > 1000:
        raise HTTPException(422, 'Terlalu banyak akses')
    if len(db.query(User.id).filter(User.id.in_(ids)).all()) != len(ids):
        raise HTTPException(422, 'Pengguna tidak ditemukan')
    # Stage 4a: access on legacy_home is no longer mandatory for non-admins.
    if db.query(User.id).filter(User.id.in_(ids), User.role == 'admin').first():
        raise HTTPException(422, 'Admin global tidak menggunakan akses unit')
    if target_unit.level == 'up3' and any(entry.role != 'management' for entry in body.entries):
        raise HTTPException(422, 'Pengguna UP3 selain admin hanya dapat melihat')
    if any(entry.role == 'admin' for entry in body.entries):
        raise HTTPException(422, 'Tidak ada peran admin unit')
    before = {entry.user_id: entry.role for entry in access_rows(db, id)}
    # Preserve legacy admin-global assignments; they are not editable as unit grants.
    admins = {row.id for row in db.query(User.id).filter(User.role == 'admin').all()}
    editable = db.query(UserUnitAccess).filter_by(unit_id=id)
    if admins:
        editable = editable.filter(~UserUnitAccess.user_id.in_(admins))
    editable.delete(synchronize_session=False)
    db.add_all(UserUnitAccess(user_id=entry.user_id, unit_id=id, role=entry.role)
               for entry in body.entries)
    _audit(db, user, 'org_unit_access', str(id), {'before': before,
          'after': {entry.user_id: entry.role for entry in body.entries}})
    db.commit()
    return {'ok': True}
