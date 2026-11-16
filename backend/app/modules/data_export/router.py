"""Custom CSV/XLSX export and reusable export templates; authenticated, CSRF-guarded."""
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import status_summary
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from ...db import AuditLog, Metric, User, get_db
from ...security import current_user
from .models import ExportTemplate
from .renderer import render_file
from .service import export_rows, headers, validate_spec

router = APIRouter(prefix='/api/data-export', tags=['Custom Data Export'], dependencies=[Depends(unit_context('read'))])


class ExportSpec(BaseModel):
    columns: list[str] = Field(min_length=2, max_length=45)
    granularity: str = 'hour'
    aggregation: str = 'avg'
    headers: dict[str, str] = Field(default_factory=dict)
    unit_overrides: dict[str, str] = Field(default_factory=dict)
    format: str = 'xlsx'

    @field_validator('format')
    @classmethod
    def check_format(cls, value):
        if value not in ('xlsx', 'csv'):
            raise ValueError('Format hanya xlsx atau csv')
        return value


class ExportRequest(ExportSpec):
    start: date
    end: date


class SaveTemplate(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    scope: str = 'personal'
    spec: ExportSpec

    @field_validator('scope')
    @classmethod
    def check_scope(cls, value):
        if value not in {'personal', 'system'}:
            raise ValueError('Scope tidak valid')
        return value


class UpdateTemplate(SaveTemplate):
    expected_version: int = Field(ge=1)


def _serial(item):
    return {'id': item.id, 'name': item.name, 'scope': item.scope,
            'owner_id': item.owner_id, 'version': item.version,
            'archived': item.archived, 'spec': item.spec}


def _get(db, user, item_id, unit_id):
    item = db.get(ExportTemplate, item_id)
    if not item or item.unit_id != unit_id or item.archived or not (item.scope == 'system' or item.owner_id == user.id):
        raise HTTPException(404, 'Template tidak ditemukan')
    return item


@router.get('/catalog')
def catalog(u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    return {'metrics': [{'code': m.code, 'name': m.name, 'unit': m.unit, 'active': m.active}
                        for m in db.query(Metric).filter_by(unit_id=ctx.id).order_by(Metric.display_order).all()],
            'meta': ['tanggal', 'jam', 'status']}


@router.get('/templates')
def templates(u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    records = db.query(ExportTemplate).filter(
        ExportTemplate.archived.is_(False), ExportTemplate.unit_id==ctx.id,
        (ExportTemplate.scope == 'system') | (ExportTemplate.owner_id == u.id)).order_by(
            ExportTemplate.scope, ExportTemplate.name).all()
    return [_serial(r) for r in records]


@router.post('/templates', status_code=201)
def save_template(body: SaveTemplate, u: User = Depends(current_user),
                  db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    if body.scope == 'system' and u.role != 'admin':
        raise HTTPException(403, 'Template bersama hanya untuk admin')
    spec = body.spec.model_dump()
    validate_spec(db, spec, date(2026, 1, 1), date(2026, 1, 1),ctx.id)
    owner = 0 if body.scope == 'system' else u.id
    if db.query(ExportTemplate).filter_by(owner_id=owner, scope=body.scope, archived=False, unit_id=ctx.id).count() >= 100:
        raise HTTPException(422, 'Maksimal 100 template aktif')
    item = ExportTemplate(name=body.name, owner_id=owner, scope=body.scope, spec=spec, unit_id=ctx.id)
    db.add(item); db.flush()
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='export_template_create', target=str(item.id), detail={'unit_id':ctx.id,'name': body.name}))
    db.commit()
    return _serial(item)


@router.put('/templates/{template_id}')
def update_template(template_id: int, body: UpdateTemplate,
                    u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _get(db, u, template_id, ctx.id)
    if ((item.scope == 'system' and u.role != 'admin') or
            (item.scope == 'personal' and item.owner_id != u.id)):
        raise HTTPException(403, 'Tidak berhak mengubah template')
    if body.scope != item.scope:
        raise HTTPException(422, 'Jenis template tidak boleh diubah')
    if body.expected_version != item.version:
        raise HTTPException(409, 'Template sudah diubah di sesi lain')
    spec = body.spec.model_dump()
    validate_spec(db, spec, date(2026, 1, 1), date(2026, 1, 1),ctx.id)
    changed = db.execute(update(ExportTemplate).where(
        ExportTemplate.id == item.id, ExportTemplate.version == body.expected_version).values(
        name=body.name, spec=spec, version=body.expected_version+1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Template sudah diubah di sesi lain')
    db.refresh(item)
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='export_template_update', target=str(item.id),
                    detail={'version': item.version}))
    db.commit()
    return _serial(item)


@router.post('/templates/{template_id}/archive')
def archive_template(template_id: int, u: User = Depends(current_user),
                     db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _get(db, u, template_id, ctx.id)
    if item.scope == 'system' and u.role != 'admin' or item.scope == 'personal' and item.owner_id != u.id:
        raise HTTPException(403, 'Tidak boleh mengarsipkan template ini')
    item.archived = True
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='export_template_archive', target=str(item.id), detail={}))
    db.commit()
    return {'ok': True}


@router.post('/preview')
def preview(body: ExportRequest, u: User = Depends(current_user),
            db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    spec = body.model_dump(exclude={'start', 'end'})
    metrics, units = validate_spec(db, spec, body.start, body.end,ctx.id)
    from itertools import islice
    sample = list(islice(export_rows(db, spec, body.start, body.end, metrics, units,ctx.id), 10))
    return {'headers': headers(spec, metrics), 'rows': sample,
            'source_status': status_summary(db, ctx.id,
                [c for c in spec['columns'] if c not in {'tanggal','jam','status'}], body.end),
            'preview_rows': len(sample), 'note': 'Pratinjau maksimal 10 baris; data kosong bukan nol.'}


@router.post('/download')
def download(body: ExportRequest, u: User = Depends(current_user),
             db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    spec = body.model_dump(exclude={'start', 'end'})
    metrics, units = validate_spec(db, spec, body.start, body.end,ctx.id)
    path = render_file(headers(spec, metrics),
                       export_rows(db, spec, body.start, body.end, metrics, units,ctx.id), body.format)
    db.add(AuditLog(user_id=u.id, unit_id=ctx.id, action='data_custom_export', target='readings',
                    detail={'start': str(body.start), 'end': str(body.end),
                            'format': body.format, 'columns': spec['columns']}))
    db.commit()
    suffix = body.format
    return FileResponse(path, filename=f'BerauLoad_{body.start}_{body.end}.{suffix}',
                        media_type=('text/csv; charset=utf-8' if suffix == 'csv' else
                                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        background=BackgroundTask(Path(path).unlink, missing_ok=True))
