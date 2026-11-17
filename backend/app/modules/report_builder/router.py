"""Report template CRUD, previews, and read-only export endpoints."""
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import metric_catalog
from datetime import date
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import update
from sqlalchemy.orm import Session
from ...db import Metric, AuditLog, User, get_db
from ...security import current_user
from .models import ReportTemplate
from .schemas import ReportCreate, ReportUpdate, ReportPreview
from .service import MAX_TEMPLATES, validate_blocks, render_blocks
from .renderers import render_pdf, render_xlsx
from ..branding.service import current as branding_current, slug as brand_slug

router = APIRouter(prefix='/api/report-builder', tags=['Report Builder'], dependencies=[Depends(unit_context('read'))])


def serial(item):
    return {'id': item.id, 'name': item.name, 'description': item.description,
            'scope': item.scope, 'owner_id': item.owner_id, 'blocks': item.blocks,
            'version': item.version, 'archived': item.archived}


def permitted(db, template_id, user, unit_id, edit=False):
    item = db.get(ReportTemplate, template_id)
    if not item or item.unit_id != unit_id or (item.scope != 'system' and item.owner_id != user.id):
        raise HTTPException(404, 'Template laporan tidak ditemukan')
    if edit and (item.scope == 'system' and user.role != 'admin'):
        raise HTTPException(403, 'Hanya admin dapat mengubah template sistem')
    return item


def validated(db, blocks, unit_id):
    known = {code: m.unit for code, m in metric_catalog(db, unit_id).items()}
    return validate_blocks([b.model_dump() for b in blocks], known)


def audit(db, user, action, target, unit_id):
    db.add(AuditLog(user_id=user.id, unit_id=unit_id, action=action,
                    target=f'report:{target}', detail={'unit_id':unit_id}))


@router.get('')
def list_reports(u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    rows = (db.query(ReportTemplate).filter(ReportTemplate.archived.is_(False), ReportTemplate.unit_id==ctx.id)
            .order_by(ReportTemplate.id.desc()).all())
    return [serial(x) for x in rows if x.scope == 'system' or x.owner_id == u.id]


@router.post('', status_code=201)
def create_report(body: ReportCreate, u: User = Depends(current_user),
                  db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    if body.scope == 'system' and u.role != 'admin':
        raise HTTPException(403, 'Template sistem hanya dapat dibuat admin')
    owner = 0 if body.scope == 'system' else u.id
    count = db.query(ReportTemplate).filter_by(scope=body.scope, owner_id=owner, archived=False, unit_id=ctx.id).count()
    if count >= MAX_TEMPLATES:
        raise HTTPException(422, 'Batas template aktif tercapai')
    item = ReportTemplate(name=body.name, description=body.description, scope=body.scope,
                          owner_id=owner, blocks=validated(db, body.blocks, ctx.id), updated_by=u.id, unit_id=ctx.id)
    db.add(item)
    db.flush()
    audit(db, u, 'report_create', item.id, ctx.id)
    db.commit()
    return serial(item)


@router.put('/{template_id}')
def update_report(template_id: int, body: ReportUpdate,
                  u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = permitted(db, template_id, u, ctx.id, edit=True)
    if item.archived:
        raise HTTPException(409, 'Template sudah diarsipkan')
    if body.scope != item.scope:
        raise HTTPException(422, 'Jenis kepemilikan tidak boleh diubah')
    blocks = validated(db, body.blocks, ctx.id)
    updated = db.execute(update(ReportTemplate).where(
        ReportTemplate.id == template_id, ReportTemplate.version == body.expected_version).values(
        name=body.name, description=body.description, blocks=blocks,
        updated_by=u.id, version=body.expected_version+1))
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Template diubah sesi lain; muat ulang')
    db.refresh(item)
    audit(db, u, 'report_update', item.id, ctx.id)
    db.commit()
    return serial(item)


@router.post('/{template_id}/duplicate', status_code=201)
def duplicate_report(template_id: int, u: User = Depends(current_user),
                     db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    src = permitted(db, template_id, u, ctx.id)
    payload = ReportCreate(name=('Salinan '+src.name)[:150], description=src.description,
                           blocks=src.blocks, scope='personal')
    return create_report(payload, u, db, ctx)


@router.post('/{template_id}/archive')
def archive_report(template_id: int, u: User = Depends(current_user),
                   db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = permitted(db, template_id, u, ctx.id, edit=True)
    item.archived = True
    audit(db, u, 'report_archive', item.id, ctx.id)
    db.commit()
    return {'ok': True}


@router.post('/preview')
def preview_report(body: ReportPreview, u: User = Depends(current_user),
                   db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    try:
        start, end = date.fromisoformat(body.start), date.fromisoformat(body.end)
    except ValueError:
        raise HTTPException(422, 'Tanggal tidak valid')
    return render_blocks(db, validated(db, body.blocks, ctx.id), start, end, ctx.id)


@router.get('/{template_id}/download')
def download_report(template_id: int, start: date, end: date, format: str = 'pdf',
                    u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    item = permitted(db, template_id, u, ctx.id)
    if item.archived:
        raise HTTPException(404, 'Template laporan sudah diarsipkan')
    if format not in {'pdf', 'xlsx'}:
        raise HTTPException(422, 'Format didukung: pdf, xlsx')
    content = render_blocks(db, item.blocks, start, end, ctx.id)
    brand = branding_current(db)
    data = render_pdf(item.name, content, brand) if format == 'pdf' else render_xlsx(item.name, content, brand)
    mime = 'application/pdf' if format == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return StreamingResponse(BytesIO(data), media_type=mime, headers={
        'Content-Disposition': f'attachment; filename="{brand_slug(brand["app_short_name"])}_Report_{item.id}_{start}.{format}"',
        'Cache-Control': 'no-store'})
