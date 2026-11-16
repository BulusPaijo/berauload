"""Historical calculations API. V1.2.1 edits append immutable versions."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db
from ...security import current_user, require
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import status_summary
from ..formulas.engine import FormulaError
from ..units.models import UnitDefinition
from ..units.service import profile
from .models import HistoricalRevision
from .repository import (add_definition, catalog_units, code_exists, get_definition,
                         get_definitions, get_revision, iter_readings, list_revisions)
from .service import compute, valid_definition, validate_range

router = APIRouter(prefix='/api/historical-calculations', tags=['Historical Calculations'],
                   dependencies=[Depends(unit_context('read'))])
CONFIG_FIELDS = ('expression', 'unit', 'aggregation', 'resolution', 'mode',
                 'moving_days', 'hour_start', 'hour_end')


class DefinitionInput(BaseModel):
    code: str = Field(min_length=2, max_length=90, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(min_length=2, max_length=180)
    expression: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=12)
    aggregation: str = 'AVG'
    resolution: str = 'month'
    mode: str = 'period'
    moving_days: int = 7
    hour_start: int = 0
    hour_end: int = 23

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, name):
        if name.lstrip().startswith(('=', '+', '-', '@')):
            raise ValueError('Nama tidak boleh diawali ekspresi spreadsheet')
        return name


class PreviewRequest(DefinitionInput):
    start: date
    end: date


class RenameRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)

    @field_validator('name')
    @classmethod
    def safe_name(cls, name):
        return DefinitionInput.sanitize_name(name)


class RevisionRequest(DefinitionInput):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


class ArchiveRequest(BaseModel):
    archived: bool
    reason: str = Field(min_length=5, max_length=500)


def _config(body: DefinitionInput) -> dict:
    return body.model_dump(include=set(CONFIG_FIELDS))


def _describe(item):
    return {key: getattr(item, key) for key in (
        'id', 'code', 'name', 'expression', 'unit', 'aggregation', 'resolution',
        'mode', 'moving_days', 'hour_start', 'hour_end', 'version', 'archived')}


def _run(db, cfg: dict, start: date, end: date, unit_id, include_inactive=False):
    try:
        validate_range(start, end, cfg['resolution'])
        source_units = catalog_units(db, include_inactive=include_inactive, unit_id=unit_id)
        registry = profile(db.query(UnitDefinition).all())
        refs = valid_definition(cfg, source_units, registry)
        query_start = (date(start.year - 1, start.month, 1) if cfg['mode'] == 'yoy'
                       else start - timedelta(days=cfg['moving_days'] - 1)
                       if cfg['mode'] == 'moving_avg' else start)
        result = compute(cfg, iter_readings(db, refs, query_start, end, unit_id), start, end,
                         source_units, registry)
        result['source_status'] = status_summary(db, unit_id, refs, end)
        result['result_unit'] = '%' if cfg['mode'] == 'yoy' else (
            'jam' if cfg['aggregation'] == 'SUM' else cfg['unit'])
        return result
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc


def _load(db, definition_id: int, unit_id):
    item = get_definition(db, definition_id, unit_id)
    if item is None:
        raise HTTPException(404, 'Perhitungan historis tidak ditemukan')
    return item


def _log(db, user, action: str, item, detail: dict):
    db.add(AuditLog(user_id=user.id, unit_id=item.unit_id, action=action, target=item.code, detail=detail))


@router.get('')
def list_definitions(include_archived: bool = False, u: User = Depends(current_user),
                     db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    if include_archived and u.role != 'admin':
        raise HTTPException(403, 'Hanya admin dapat melihat arsip')
    return [_describe(item) for item in get_definitions(db, include_archived, ctx.id)]


@router.post('/preview')
def preview(body: PreviewRequest, u: User = Depends(require('admin')),
            db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    return _run(db, _config(body), body.start, body.end, ctx.id)


@router.post('', status_code=201)
def create(body: DefinitionInput, u: User = Depends(require('admin')),
           db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    try:
        refs = valid_definition(_config(body), catalog_units(db, unit_id=ctx.id), profile(db.query(UnitDefinition).all()))
        if code_exists(db, body.code):
            raise HTTPException(409, 'Kode perhitungan historis sudah digunakan')
        saved = add_definition(db, {**body.model_dump(), 'unit_id':ctx.id}, u.id)
        _log(db, u, 'historical_formula_create', saved,
             {'references': sorted(refs), 'expression': body.expression, 'version': 1})
        db.commit()
        return _describe(saved)
    except FormulaError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.patch('/{definition_id}/name')
def rename(definition_id: int, body: RenameRequest, u: User = Depends(require('admin')),
           db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _load(db, definition_id, ctx.id)
    previous = item.name
    item.name = body.name
    _log(db, u, 'historical_formula_rename', item, {'from': previous, 'to': item.name})
    db.commit()
    return _describe(item)


@router.post('/{definition_id}/revisions', status_code=201)
def revise(definition_id: int, body: RevisionRequest, u: User = Depends(require('admin')),
           db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _load(db, definition_id, ctx.id)
    if item.archived:
        raise HTTPException(409, 'Pulihkan dari arsip sebelum merevisi')
    if body.code != item.code:
        raise HTTPException(422, 'Kode unik tidak dapat diubah')
    if body.expected_version != item.version:
        raise HTTPException(409, 'Formula telah diubah pengguna lain; muat ulang')
    try:
        refs = valid_definition(_config(body), catalog_units(db, include_inactive=True,unit_id=ctx.id),
                                profile(db.query(UnitDefinition).all()))
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc
    previous = item.version
    for field in ('name', *CONFIG_FIELDS):
        setattr(item, field, getattr(body, field))
    item.version = previous + 1
    snapshot = {field: getattr(item, field) for field in ('code', 'name', *CONFIG_FIELDS)}
    db.add(HistoricalRevision(definition_id=item.id, version=item.version,
                              snapshot=snapshot, reason=body.reason, created_by=u.id))
    _log(db, u, 'historical_formula_revision', item,
         {'previous_version': previous, 'version': item.version,
          'reason': body.reason, 'references': sorted(refs)})
    db.commit()
    return _describe(item)


@router.patch('/{definition_id}/archive')
def archive(definition_id: int, body: ArchiveRequest, u: User = Depends(require('admin')),
            db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _load(db, definition_id, ctx.id)
    item.archived = body.archived
    _log(db, u, 'historical_formula_archive' if body.archived else 'historical_formula_restore',
         item, {'reason': body.reason, 'version': item.version})
    db.commit()
    return _describe(item)


@router.get('/{definition_id}/revisions')
def revisions(definition_id: int, u: User = Depends(current_user),
              db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    _load(db, definition_id, ctx.id)
    return [{'version': r.version, 'snapshot': r.snapshot, 'reason': r.reason,
             'created_at': r.created_at, 'created_by': r.created_by}
            for r in list_revisions(db, definition_id)]


@router.get('/{definition_id}/run')
def run_saved(definition_id: int, start: date, end: date, version: int | None = None,
              u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    item = _load(db, definition_id, ctx.id)
    if item.archived and version is None:
        raise HTTPException(409, 'Formula diarsipkan; pilih versi historis secara eksplisit')
    if version is not None:
        revision = get_revision(db, definition_id, version)
        if revision is None:
            raise HTTPException(404, 'Versi formula tidak ditemukan')
        cfg = {field: revision.snapshot[field] for field in CONFIG_FIELDS}
        label = revision.snapshot['name']
    else:
        cfg = {field: getattr(item, field) for field in CONFIG_FIELDS}
        label = item.name
    result = _run(db, cfg, start, end, ctx.id, include_inactive=True)
    return {'definition': _describe(item), 'evaluated_version': version or item.version,
            'evaluated_name': label, **result}
