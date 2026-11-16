"""HTTP surface of V1.1 Formula Builder; V1 endpoints remain unchanged."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from ...db import AuditLog, HourRecord, Reading, Metric, User, get_db
from ..units.models import UnitDefinition
from ..units.service import profile
from ...security import current_user, require
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import metric_catalog, validate_codes, status_summary
from .engine import FormulaError, parse_formula
from .repository import (create, existing_asset, list_formulas, list_metrics,
                         next_display_order)
from .service import calculate_custom, dependency_order, preview, validate_candidate

router = APIRouter(prefix='/api/formulas', tags=['Formula Builder'])
GROUPS = ('PEMBANGKIT', 'KUALITAS', 'FEEDER', 'REKAP', 'REKAP_LAIN')


class FormulaCreate(BaseModel):
    code: str = Field(min_length=2, max_length=90, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(min_length=2, max_length=180)
    unit: str = Field(min_length=1, max_length=12)
    group_name: str = 'REKAP'
    asset_id: int | None = None
    expression: str = Field(min_length=1, max_length=500)

    @field_validator('name')
    @classmethod
    def safe_name(cls, value):
        if value.lstrip().startswith(('=', '+', '-', '@')):
            raise ValueError('Nama parameter tidak boleh diawali simbol formula Excel')
        return value

    @field_validator('group_name')
    @classmethod
    def valid_group(cls, value):
        if value not in GROUPS:
            raise ValueError('Kelompok tidak valid')
        return value


class FormulaPreview(BaseModel):
    expression: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=12)
    samples: dict[str, float | None] = Field(default_factory=dict)


@router.get('')
def all_formulas(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    return [{'code': m.code, 'name': m.name, 'unit': m.unit, 'expression': d.expression,
             'version': d.version, 'active': m.active, 'locked': True,
             'created_at': d.created_at.isoformat() if d.created_at else None}
            for d, m in list_formulas(db) if m.unit_id==ctx.id]


@router.post('/preview')
def preview_formula(body: FormulaPreview, u: User = Depends(require('admin')),
                    ctx:UnitContext=Depends(unit_context('configure')),
                    db: Session = Depends(get_db)):
    units = {code: m.unit for code, m in metric_catalog(db, ctx.id).items()}
    try:
        return preview(body.expression, body.unit, body.samples, units,
                       profile(db.query(UnitDefinition).filter_by(active=True).all()))
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('', status_code=201)
def create_formula(body: FormulaCreate, u: User = Depends(require('admin')),
                   ctx:UnitContext=Depends(unit_context('configure')),
                   db: Session = Depends(get_db)):
    if not existing_asset(db, body.asset_id):
        raise HTTPException(422, 'Peralatan tidak ditemukan')
    from ...db import Asset
    if body.asset_id is not None and not db.query(Asset.id).filter_by(
            id=body.asset_id, unit_id=ctx.id).first():
        raise HTTPException(404,'Peralatan tidak ditemukan')
    try:
        spec = validate_candidate(db, body.code, body.unit, body.expression)
        validate_codes(db, ctx.id, spec.variables)
        candidate = Metric(code=body.code, name=body.name, unit=body.unit,
                           group_name=body.group_name, asset_id=body.asset_id,
                           input_mode='computed', display_order=next_display_order(db), active=True,
                           unit_id=ctx.id)
        entry = create(db, candidate, body.expression, u.id)
        dependency_order(list_formulas(db))
        db.add(AuditLog(user_id=u.id, action='formula_created', target=body.code,
                        detail={'unit_id':ctx.id,'actor_role':'admin_global','expression': body.expression, 'unit': body.unit,
                                'dependencies': sorted(spec.variables), 'version': 1}))
        db.commit()
        return {'ok': True, 'id': entry.id, 'code': body.code, 'version': 1,
                'note': 'Formula aktif pada pembacaan baru; tidak mengubah histori lama.'}
    except FormulaError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get('/completeness')
def completeness(day: date, hour: int,
                 ctx: UnitContext = Depends(unit_context('read')),
                 db: Session = Depends(get_db)):
    if not 0 <= hour <= 23:
        raise HTTPException(422, 'Jam harus 0–23')
    record = db.query(HourRecord).filter_by(day=day, hour=hour).first()
    available = set()
    if record:
        available = {code for code, in db.query(Metric.code).join(
            Reading, Reading.metric_id == Metric.id).filter(
            Reading.hour_id == record.id).all()}
    catalog = metric_catalog(db, ctx.id, include_inactive=True)
    items = []
    for formula, target in list_formulas(db):
        if target.unit_id != ctx.id:
            continue
        refs = parse_formula(formula.expression)[1]
        visible = set(refs) & catalog.keys()
        items.append({'code': target.code, 'name': target.name,
                      'filled': len(visible & available), 'sources': len(refs),
                      'complete': len(visible & available) == len(refs),
                      'label': f'{len(visible & available)} dari {len(refs)} sumber terisi'})
    return {'day': day.isoformat(), 'hour': hour, 'formulas': items}
