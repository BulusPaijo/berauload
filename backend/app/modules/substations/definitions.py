"""Global admin-controlled definitions; immutable codes once created."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .common import audit, check_code, dump, require_admin
from .models import (SubstationParam, SubstationSession, SubstationValueFlag,
                     SubstationField, SubstationChoice, SubstationValue)
from .schemas import DefinitionForm, DefinitionPatch

router = APIRouter(prefix='/api/substations', tags=['Substation Definitions'])
KINDS = {'params': SubstationParam, 'sessions': SubstationSession,
         'flags': SubstationValueFlag, 'fields': SubstationField,
         'ownership': SubstationChoice, 'purpose': SubstationChoice}


def shape(kind, source, create):
    fields = {column.name for column in KINDS[kind].__table__.columns}
    data = {key: value for key, value in source.items() if key in fields and key != 'id'}
    if kind in ('ownership', 'purpose'):
        data['kind'] = kind
    if kind == 'fields':
        data['kind'] = source.get('kind') or 'text'
        if data['kind'] not in ('text', 'number', 'choice'):
            raise HTTPException(422, 'Jenis atribut tidak dikenal')
    if kind == 'params':
        if 'min_value' in data and 'max_value' in data and (
            data['min_value'] is not None and data['max_value'] is not None and
            data['min_value'] > data['max_value']):
            raise HTTPException(422, 'Batas minimum lebih tinggi dari maksimum')
    if create:
        check_code(data['code'])
    return data


@router.get('/definitions')
def list_definitions(db: Session = Depends(get_db),
                     ctx: UnitContext = Depends(unit_context('read'))):
    return {kind: [dump(row) for row in db.query(model).order_by(
        model.display_order, model.id)] if kind not in ('ownership','purpose')
        else [dump(row) for row in db.query(model).filter_by(kind=kind).order_by(
        model.display_order, model.id)]
        for kind, model in KINDS.items()}


@router.post('/definitions/{kind}')
def add_definition(kind: str, body: DefinitionForm,
                   ctx: UnitContext = Depends(unit_context('read')),
                   db: Session = Depends(get_db)):
    require_admin(ctx)
    if kind not in KINDS:
        raise HTTPException(404, 'Definisi tidak dikenal')
    model = KINDS[kind]
    key = {'code': body.code}
    if kind in ('ownership', 'purpose'):
        key['kind'] = kind
    if db.query(model.id).filter_by(**key).first():
        raise HTTPException(409, 'Kode definisi sudah terdaftar')
    row = model(**shape(kind, body.model_dump(exclude_none=True), True))
    try:
        db.add(row); db.flush()
        audit(db, ctx, 'substation_definition_create', f'{kind}/{row.code}', after=dump(row))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode definisi sudah terdaftar') from exc
    return dump(row)


@router.patch('/definitions/{kind}/{id}')
def edit_definition(kind: str, id: int, body: DefinitionPatch,
                    ctx: UnitContext = Depends(unit_context('read')),
                    db: Session = Depends(get_db)):
    require_admin(ctx)
    if kind not in KINDS:
        raise HTTPException(404, 'Definisi tidak dikenal')
    row = db.get(KINDS[kind], id)
    if row is None or (kind in ('ownership', 'purpose') and row.kind != kind):
        raise HTTPException(404, 'Definisi tidak ditemukan')
    values = shape(kind, body.model_dump(exclude_unset=True), False)
    if 'code' in values and values.pop('code') != row.code:
        raise HTTPException(409, 'Kode definisi permanen dan tidak dapat diganti')
    if kind == 'params':
        minimum = values.get('min_value', row.min_value)
        maximum = values.get('max_value', row.max_value)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(422, 'Batas minimum lebih tinggi dari maksimum')
    if kind == 'params' and 'scope' in values and values['scope'] != row.scope and db.query(SubstationValue.id).filter_by(param_id=id).first():
        raise HTTPException(409, 'Cakupan parameter tidak boleh berubah setelah pengukuran')
    before = dump(row)
    for key, value in values.items():
        if key != 'kind':
            setattr(row, key, value)
    if before != dump(row):
        audit(db, ctx, 'substation_definition_update', f'{kind}/{row.code}', before, dump(row))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode definisi sudah terdaftar') from exc
    return dump(row)
