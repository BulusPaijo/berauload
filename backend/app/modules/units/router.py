"""Admin-managed units with immutable dimensions and conversion factors."""
from decimal import Decimal
from hashlib import sha256
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from ...db import AuditLog, Metric, User, get_db
from ...security import current_user, require
from .models import UnitDefinition
from .service import UnitError, convert, profile

router = APIRouter(prefix='/api/units', tags=['Master Satuan'])


class NewUnit(BaseModel):
    code: str = Field(min_length=1, max_length=12, pattern=r'^[A-Za-z0-9%—/_-]+$')
    name: str = Field(min_length=2, max_length=100)
    dimension: str = Field(min_length=2, max_length=40, pattern=r'^[a-z][a-z0-9_]*$')
    factor: Decimal = Field(gt=Decimal('0'), lt=Decimal('1e12'))

    @field_validator('factor')
    @classmethod
    def precise(cls, value):
        if value.as_tuple().exponent < -12:
            raise ValueError('Faktor maksimal 12 angka desimal')
        return value


class Status(BaseModel):
    active: bool


def _serial(r):
    return {'code': r.code, 'name': r.name, 'dimension': r.dimension,
            'factor': float(r.factor), 'active': r.active, 'builtin': r.builtin}


@router.get('')
def list_units(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_serial(r) for r in db.query(UnitDefinition).order_by(UnitDefinition.dimension, UnitDefinition.code)]


@router.post('', status_code=201)
def add_unit(body: NewUnit, u: User = Depends(require('admin')), db: Session = Depends(get_db)):
    if db.query(UnitDefinition).filter_by(code=body.code).first():
        raise HTTPException(409, 'Kode satuan sudah ada dan tidak boleh diganti')
    payload = body.model_dump()
    # 'other_custom' is a UI sentinel; never group unrelated custom units.
    if payload['dimension'] == 'other_custom':
        payload['dimension'] = 'custom_' + sha256(body.code.encode('utf-8')).hexdigest()[:16]
    row = UnitDefinition(**payload, active=True, builtin=False)
    db.add(row)
    db.add(AuditLog(user_id=u.id, action='unit_create', target=body.code,
                    detail={'dimension': row.dimension, 'factor': str(body.factor)}))
    db.commit()
    return _serial(row)


@router.put('/{code}/status')
def update_status(code: str, body: Status, u: User = Depends(require('admin')),
                  db: Session = Depends(get_db)):
    row = db.query(UnitDefinition).filter_by(code=code).first()
    if not row:
        raise HTTPException(404, 'Satuan tidak ditemukan')
    if not body.active:
        if row.builtin:
            raise HTTPException(409, 'Satuan standar tidak boleh dinonaktifkan')
        if db.query(Metric.id).filter_by(unit=code).first():
            raise HTTPException(409, 'Satuan sedang digunakan parameter; jangan dinonaktifkan')
    row.active = body.active
    db.add(AuditLog(user_id=u.id, action='unit_status', target=code,
                    detail={'active': body.active}))
    db.commit()
    return _serial(row)


@router.get('/convert')
def convert_preview(value: float, source: str, target: str,
                    u: User = Depends(current_user), db: Session = Depends(get_db)):
    mapping = profile(db.query(UnitDefinition).all())
    try:
        return {'result': convert(value, mapping[source], mapping[target]), 'unit': target}
    except KeyError as exc:
        raise HTTPException(422, 'Satuan tidak dikenal') from exc
    except UnitError as exc:
        raise HTTPException(422, str(exc)) from exc
