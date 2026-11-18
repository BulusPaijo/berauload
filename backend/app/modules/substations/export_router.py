"""Stage 9d-2: export builder + templates API (reuses 9c filter as single source)."""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .analysis_queries import filtered
from .analysis_router import AnalysisOptions, validate_options
from .common import audit, dump
from .export_builder import (MAX_LONG, MAX_WIDE, PREVIEW, check_spec, filename, generate,
                             total_rows, write_file)
from .export_catalog import catalog, missing_keys
from .export_models import GarduExportTemplate

router = APIRouter(prefix='/api/substations/export', tags=['Gardu Export'])


class ExportBody(BaseModel):
    filter: dict = Field(default_factory=dict)
    spec: dict


class TemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    shared: bool = False
    spec: dict
    expected_version: int | None = None


def options_from(db, raw):
    try:
        opt = AnalysisOptions(**{**raw, 'page': 1, 'page_size': 50})
    except Exception:
        raise HTTPException(422, 'Filter ekspor tidak sah')
    return validate_options(db, opt)


def limit_of(shape):
    return MAX_LONG if shape == 'long' else MAX_WIDE


@router.get('/catalog')
def get_catalog(db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    return {'columns': catalog(db), 'limits': {'wide': MAX_WIDE, 'long': MAX_LONG, 'preview': PREVIEW}}


@router.post('/preview')
def preview(body: ExportBody, db: Session = Depends(get_db),
            ctx: UnitContext = Depends(unit_context('read'))):
    keys, shape, _, _ = check_spec(db, body.spec)
    opt = options_from(db, body.filter)
    query = filtered(db, ctx, opt)
    total = total_rows(db, query, shape)
    rows = list(generate(db, query, opt, keys, shape, limit=PREVIEW))[:PREVIEW]
    from .export_builder import LONG_TAIL
    headers = [h for _, h in keys] + (LONG_TAIL if shape == 'long' else [])
    return {'headers': headers, 'rows': rows, 'total': total, 'limit': limit_of(shape),
            'over_limit': total > limit_of(shape)}


@router.post('/download')
def download(body: ExportBody, db: Session = Depends(get_db),
             ctx: UnitContext = Depends(unit_context('read'))):
    keys, shape, fmt, delim = check_spec(db, body.spec)
    opt = options_from(db, body.filter)
    query = filtered(db, ctx, opt)
    total = total_rows(db, query, shape)
    if total > limit_of(shape):
        raise HTTPException(422, f'Ekspor dibatasi {limit_of(shape)} baris (ada {total}). Persempit filter.')
    path = write_file(db, query, opt, keys, shape, fmt, delim, total)
    from ..branding.models import AppBranding
    brand = db.get(AppBranding, 1)
    audit(db, ctx, 'gardu_export', 0, after={'rows': total, 'shape': shape, 'format': fmt,
          'columns': len(keys), 'filter': opt.model_dump(mode='json')})
    db.commit()
    media = ('text/csv; charset=utf-8' if fmt == 'csv' else
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return FileResponse(path, media_type=media, background=BackgroundTask(os.unlink, path),
                        filename=filename(brand.app_short_name if brand else None, fmt))


def visible(db, ctx, include_archived=False):
    q = db.query(GarduExportTemplate).filter(
        (GarduExportTemplate.shared.is_(True)) | (GarduExportTemplate.owner_id == ctx.actor.id))
    if not include_archived:
        q = q.filter(GarduExportTemplate.archived.is_(False))
    return q.order_by(GarduExportTemplate.shared.desc(), GarduExportTemplate.name).all()


def view(db, row):
    return {**dump(row), 'warnings': missing_keys(db, (row.spec or {}).get('columns', []))}


@router.get('/templates')
def list_templates(include_archived: bool = False, db: Session = Depends(get_db),
                   ctx: UnitContext = Depends(unit_context('read'))):
    return [view(db, r) for r in visible(db, ctx, include_archived)]


def writable(row, ctx):
    if row.shared and not ctx.superadmin:
        raise HTTPException(403, 'Template bersama hanya dapat diubah admin')
    if not row.shared and row.owner_id != ctx.actor.id:
        raise HTTPException(403, 'Bukan template Anda')


@router.post('/templates')
def create_template(body: TemplateBody, db: Session = Depends(get_db),
                    ctx: UnitContext = Depends(unit_context('read'))):
    check_spec(db, body.spec)
    if body.shared and not ctx.superadmin:
        raise HTTPException(403, 'Hanya admin membuat template bersama')
    row = GarduExportTemplate(owner_id=ctx.actor.id, name=body.name.strip(),
                              shared=body.shared, spec=body.spec)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Nama template sudah dipakai')
    audit(db, ctx, 'gardu_export_template', row.id, None, dump(row))
    db.commit()
    return view(db, row)


@router.put('/templates/{template_id}')
def update_template(template_id: int, body: TemplateBody, db: Session = Depends(get_db),
                    ctx: UnitContext = Depends(unit_context('read'))):
    row = db.get(GarduExportTemplate, template_id)
    if row is None or row.archived:
        raise HTTPException(404, 'Template tidak ditemukan')
    writable(row, ctx)
    if body.expected_version != row.version:
        raise HTTPException(409, 'Template sudah diubah pihak lain. Muat ulang.')
    check_spec(db, body.spec)
    before = dump(row)
    row.name, row.spec, row.version = body.name.strip(), body.spec, row.version + 1
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Nama template sudah dipakai')
    audit(db, ctx, 'gardu_export_template', row.id, before, dump(row))
    db.commit()
    return view(db, row)


@router.post('/templates/{template_id}/archive')
def archive_template(template_id: int, db: Session = Depends(get_db),
                     ctx: UnitContext = Depends(unit_context('read'))):
    row = db.get(GarduExportTemplate, template_id)
    if row is None:
        raise HTTPException(404, 'Template tidak ditemukan')
    writable(row, ctx)
    before = dump(row)
    row.archived, row.version = True, row.version + 1
    audit(db, ctx, 'gardu_export_template', row.id, before, dump(row))
    db.commit()
    return {'ok': True}
