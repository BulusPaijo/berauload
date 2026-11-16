"""CRUD for personal/system dashboards; no access to measurement write operations."""
from ..org_units.context import UnitContext, unit_context
from ..org_units.repository import home_unit
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import update
from sqlalchemy.orm import Session
from ...db import AuditLog, Metric, User, get_db
from ...security import current_user, require
from ..historical.models import HistoricalDefinition
from ..engineering.models import EngineeringRule
from .models import DashboardLayout, DashboardRevision, DashboardShare
from .repository import visible, clear_default, count_active, record_revision
from .service import MAX_DASHBOARDS, may_edit, may_view, validate_panels
from .migrations import DEFAULT_PANELS
from ..units.models import UnitDefinition
from ..org_units.repository import home_unit
from ..org_units.roles import main_pair
from ..org_units.references import metric_catalog

router = APIRouter(prefix='/api/dashboard-builder', tags=['Dashboard Builder'], dependencies=[Depends(unit_context('read'))])


class PanelInput(BaseModel):
    id: str = Field(min_length=3, max_length=60, pattern=r'^[a-zA-Z0-9_-]+$')
    title: str = Field(min_length=2, max_length=120)
    kind: str
    source: str = 'metric'
    metric_codes: list[str] = Field(default_factory=list, max_length=4)
    source_id: int | None = Field(default=None, ge=1)
    aggregation: str = 'avg'
    w: int = Field(default=6, ge=3, le=12)
    h: int = Field(default=1, ge=1, le=4)
    legend: str = 'bottom'
    decimals: int = Field(default=2, ge=0, le=4)
    display_unit: str | None = Field(default=None, max_length=12)
    colors: dict[str, str] = Field(default_factory=dict, max_length=4)
    show_points: bool = False
    style_preset: str = 'classic'
    font_family: str = 'system'
    title_font_size: int = Field(default=13, ge=11, le=24)
    value_font_size: int = Field(default=32, ge=18, le=54)
    text_color: str | None = None
    background_color: str | None = None
    border_color: str | None = None


class CreateLayout(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    description: str = Field(default='', max_length=500)
    scope: str = 'personal'
    panels: list[PanelInput] = Field(default_factory=list, max_length=16)

    @field_validator('scope')
    @classmethod
    def check_scope(cls, value):
        if value not in {'personal', 'system'}:
            raise ValueError('Scope tidak valid')
        return value


class UpdateLayout(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    description: str = Field(default='', max_length=500)
    expected_version: int = Field(ge=1)
    panels: list[PanelInput] = Field(max_length=16)


def _serial(item: DashboardLayout, db: Session, unit_id: int):
    cap, load = main_pair(db, unit_id)
    configured = bool(cap and load)
    panels = item.panels
    # Presentation-only projection for the untouched, v1 seeded system layout.
    # Never rewrite JSON/revisions or change explicit user-managed selections.
    if item.version == 1 and item.scope == 'system' and panels == DEFAULT_PANELS:
        if not configured:
            panels = []
        else:
            codes = ([cap.code, load.code], [load.code], [cap.code], [load.code])
            panels = [{**panel, 'metric_codes': list(codes[i])}
                      for i, panel in enumerate(DEFAULT_PANELS)]
    return {'id': item.id, 'name': item.name, 'description': item.description,
            'scope': item.scope, 'owner_id': item.owner_id,
            'version': item.version, 'is_default': item.is_default,
            'archived': item.archived, 'panels': panels, 'configured': configured}


def _get(db: Session, id: int, u: User, unit_id: int, edit: bool = False):
    item = db.get(DashboardLayout, id)
    shared = (item is not None and db.query(DashboardShare.id).filter_by(
        layout_id=id, user_id=u.id).first() is not None)
    if item is None or item.unit_id != unit_id or not (may_view(item, u) or shared):
        raise HTTPException(404, 'Dashboard tidak ditemukan')
    if edit and not may_edit(item, u):
        raise HTTPException(403, 'Tidak berhak mengubah dashboard ini')
    return item


def _validated(db: Session, panels: list[PanelInput], unit_id: int):
    units = {code: m.unit for code, m in metric_catalog(db, unit_id).items()}
    historical = {r.id for r in db.query(HistoricalDefinition).filter(
        HistoricalDefinition.archived.is_(False), HistoricalDefinition.unit_id==unit_id)}
    engineering = {r.id for r in db.query(EngineeringRule).filter(
        EngineeringRule.status == 'active', EngineeringRule.unit_id==unit_id)}
    unit_specs = {r.code: r for r in db.query(UnitDefinition).all()}
    cap, load = main_pair(db, unit_id)
    pair = (cap.code, load.code) if cap and load else None
    return validate_panels([p.model_dump() for p in panels], units, historical,
                           engineering, unit_specs, pair)


def _audit(db, u, event, item, detail=None):
    db.add(AuditLog(user_id=u.id, unit_id=item.unit_id, action=event, target=f'dashboard:{item.id}', detail=detail or {}))


@router.get('')
def dashboards(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    items = visible(db, u.id, ctx.id)
    personal = next((r.id for r in items if r.scope == 'personal' and r.owner_id == u.id and r.is_default), None)
    system = next((r.id for r in items if r.scope == 'system' and r.is_default), None)
    return {'items': [_serial(r, db, ctx.id) for r in items], 'effective_default_id': personal or system,
            'system_default_id': system, 'personal_default_id': personal}


@router.get('/{id}')
def read_dashboard(id: int, u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    item = _get(db, id, u, ctx.id)
    if item.archived:
        raise HTTPException(404, 'Dashboard telah diarsipkan')
    return _serial(item, db, ctx.id)


@router.post('', status_code=201)
def create_dashboard(body: CreateLayout, u: User = Depends(require('admin')),
                     db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    if body.scope == 'system' and u.role != 'admin':
        raise HTTPException(403, 'Dashboard sistem hanya dapat dibuat admin')
    owner = 0 if body.scope == 'system' else u.id
    if count_active(db, body.scope, owner, ctx.id) >= MAX_DASHBOARDS:
        raise HTTPException(422, f'Maksimal {MAX_DASHBOARDS} dashboard aktif per scope')
    panels = _validated(db, body.panels, ctx.id)
    item = DashboardLayout(name=body.name, description=body.description, scope=body.scope,
                           owner_id=owner, panels=panels, updated_by=u.id, unit_id=ctx.id)
    db.add(item)
    db.flush()
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_create', item, {'scope': body.scope})
    db.commit()
    return _serial(item, db, ctx.id)


@router.put('/{id}')
def update_dashboard(id: int, body: UpdateLayout, u: User = Depends(require('admin')),
                     db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    if item.archived:
        raise HTTPException(409, 'Pulihkan dashboard dari arsip untuk mengedit')
    if body.expected_version != item.version:
        raise HTTPException(409, 'Dashboard sudah diubah di sesi lain; muat ulang')
    panels = _validated(db, body.panels, ctx.id)
    # Atomic compare-and-swap, not only an in-memory version check.
    changed = db.execute(update(DashboardLayout).where(
        DashboardLayout.id == id, DashboardLayout.version == body.expected_version).values(
        name=body.name, description=body.description, panels=panels,
        version=body.expected_version + 1, updated_by=u.id))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Dashboard diubah sesi lain; muat ulang')
    db.refresh(item)
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_update', item, {'version': item.version, 'panels': len(panels)})
    db.commit()
    return _serial(item, db, ctx.id)


@router.post('/{id}/duplicate', status_code=201)
def duplicate_dashboard(id: int, u: User = Depends(require('admin')),
                        db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    source = _get(db, id, u, ctx.id)
    if source.archived:
        raise HTTPException(409, 'Dashboard diarsipkan')
    if count_active(db, 'personal', u.id, ctx.id) >= MAX_DASHBOARDS:
        raise HTTPException(422, 'Jumlah dashboard pribadi sudah maksimum')
    item = DashboardLayout(name=f'Salinan {source.name}'[:150], description=source.description,
                           scope='personal', owner_id=u.id,
                           panels=[dict(p) for p in source.panels], updated_by=u.id, unit_id=ctx.id)
    db.add(item); db.flush()
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_duplicate', item, {'source_id': source.id})
    db.commit()
    return _serial(item, db, ctx.id)


@router.post('/{id}/default')
def make_default(id: int, u: User = Depends(require('admin')), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    if item.archived:
        raise HTTPException(409, 'Dashboard diarsipkan')
    clear_default(db, item.scope, item.owner_id, ctx.id)
    item.is_default = True
    _audit(db, u, 'dashboard_default', item, {'scope': item.scope})
    db.commit()
    return _serial(item, db, ctx.id)


@router.post('/{id}/archive')
def archive_dashboard(id: int, u: User = Depends(require('admin')),
                      db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    if item.archived:
        raise HTTPException(409, 'Sudah diarsipkan')
    if item.scope == 'system' and count_active(db, 'system', 0, ctx.id) <= 1:
        raise HTTPException(409, 'Dashboard sistem aktif terakhir tidak dapat diarsipkan')
    if item.is_default and item.scope == 'system':
        replacement = next((r for r in visible(db, u.id, ctx.id)
                            if r.scope == 'system' and r.id != item.id), None)
        if replacement:
            replacement.is_default = True
    item.archived = True
    item.is_default = False
    _audit(db, u, 'dashboard_archive', item)
    db.commit()
    return {'ok': True}


class ShareRequest(BaseModel):
    username: str = Field(min_length=2, max_length=70)


class RestoreVersion(BaseModel):
    revision_id: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class ImportConfig(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    description: str = Field(default='', max_length=500)
    panels: list[PanelInput] = Field(default_factory=list, max_length=16)


@router.get('/{id}/revisions')
def revisions(id: int, u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    _get(db, id, u, ctx.id)
    rows = db.query(DashboardRevision).filter_by(layout_id=id).order_by(
        DashboardRevision.version.desc()).limit(100).all()
    return [{'id': r.id, 'version': r.version, 'created_at': r.created_at,
             'updated_by': r.updated_by, 'snapshot': r.snapshot} for r in rows]


@router.post('/{id}/restore-version')
def restore_version(id: int, body: RestoreVersion, u: User = Depends(require('admin')),
                    db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    if item.archived:
        raise HTTPException(409, 'Dashboard diarsipkan')
    old = db.query(DashboardRevision).filter_by(
        id=body.revision_id, layout_id=id).first()
    if old is None:
        raise HTTPException(404, 'Versi tidak ditemukan')
    if body.expected_version != item.version:
        raise HTTPException(409, 'Dashboard sudah berubah, muat ulang')
    snap = old.snapshot
    panels = _validated(db, [PanelInput.model_validate(p) for p in snap['panels']], ctx.id)
    changed = db.execute(update(DashboardLayout).where(
        DashboardLayout.id == id, DashboardLayout.version == body.expected_version).values(
        name=snap['name'], description=snap['description'], panels=panels,
        version=body.expected_version+1, updated_by=u.id))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Versi sudah berubah')
    db.refresh(item)
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_revision_restore', item,
           {'from_revision': old.version, 'version': item.version})
    db.commit()
    return _serial(item, db, ctx.id)


@router.get('/{id}/shares')
def get_shares(id: int, u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    _get(db, id, u, ctx.id, edit=True)
    rows = db.query(User.username).join(DashboardShare,
        DashboardShare.user_id == User.id).filter(DashboardShare.layout_id == id).all()
    return [r[0] for r in rows]


@router.post('/{id}/shares')
def add_share(id: int, body: ShareRequest, u: User = Depends(require('admin')),
              db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    if item.scope != 'personal':
        raise HTTPException(422, 'Dashboard sistem sudah terlihat oleh semua pengguna')
    target = db.query(User).filter_by(username=body.username, active=True).first()
    if target is None or target.id == item.owner_id:
        raise HTTPException(422, 'Pengguna tujuan tidak ditemukan atau pemilik dashboard')
    exists = db.query(DashboardShare).filter_by(layout_id=id, user_id=target.id).first()
    if not exists:
        db.add(DashboardShare(layout_id=id, user_id=target.id))
        _audit(db, u, 'dashboard_share_add', item, {'recipient_id': target.id})
        db.commit()
    return {'ok': True}


@router.delete('/{id}/shares/{username}')
def remove_share(id: int, username: str, u: User = Depends(require('admin')),
                 db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    item = _get(db, id, u, ctx.id, edit=True)
    target = db.query(User).filter_by(username=username).first()
    if target is None:
        raise HTTPException(404, 'Pengguna tidak ditemukan')
    db.query(DashboardShare).filter_by(layout_id=id, user_id=target.id).delete()
    _audit(db, u, 'dashboard_share_remove', item, {'recipient_id': target.id})
    db.commit()
    return {'ok': True}


@router.get('/{id}/export-config')
def export_config(id: int, u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    item = _get(db, id, u, ctx.id)
    payload = {'format': 'berauload-dashboard-v1', 'name': item.name,
               'description': item.description, 'panels': item.panels}
    return JSONResponse(payload, headers={'Content-Disposition':
        f'attachment; filename="berauload-dashboard-{id}.json"',
        'X-Content-Type-Options': 'nosniff'})


@router.post('/import-config', status_code=201)
def import_config(body: ImportConfig, u: User = Depends(require('admin')),
                  db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    if count_active(db, 'personal', u.id, ctx.id) >= MAX_DASHBOARDS:
        raise HTTPException(422, 'Jumlah dashboard pribadi maksimum')
    panels = _validated(db, body.panels, ctx.id)
    item = DashboardLayout(name=body.name, description=body.description,
                           scope='personal', owner_id=u.id, panels=panels, updated_by=u.id, unit_id=ctx.id)
    db.add(item)
    db.flush()
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_import_config', item, {'panels': len(panels)})
    db.commit()
    return _serial(item, db, ctx.id)


TEMPLATE_DEFS = {
    'operasi': {'name': 'Monitoring Operasi Berau', 'codes': [], 'kind': 'line'},
    'pembangkit': {'name': 'Analisis Output PLTU Lati', 'codes': [
        'pltu_lati_cb33_kw', 'pltu_lati_cb31_kw'], 'kind': 'line'},
    'feeder': {'name': 'Arus Penyulang 1', 'codes': [
        'feeder_1_r_a', 'feeder_1_s_a', 'feeder_1_t_a'], 'kind': 'line'},
}


@router.get('/manage/templates')
def list_templates(u: User = Depends(current_user), db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('read'))):
    cap, load = main_pair(db, ctx.id)
    known = set(metric_catalog(db, ctx.id))
    return [{'key': key, 'name': item['name'],
             'configured': key != 'operasi' or bool(cap and load)}
            for key, item in TEMPLATE_DEFS.items()
            if key == 'operasi' or set(item['codes']).issubset(known)]


@router.post('/manage/templates/{key}/create', status_code=201)
def create_from_template(key: str, u: User = Depends(require('admin')),
                         db: Session = Depends(get_db), ctx: UnitContext=Depends(unit_context('configure'))):
    config = TEMPLATE_DEFS.get(key)
    if config is None:
        raise HTTPException(404, 'Template tidak ditemukan')
    if count_active(db, 'personal', u.id, ctx.id) >= MAX_DASHBOARDS:
        raise HTTPException(422, 'Jumlah dashboard pribadi maksimum')
    cap, load = main_pair(db, ctx.id)
    codes = ([cap.code, load.code] if cap and load else []) if key == 'operasi' else config['codes']
    if not codes: raise HTTPException(422, 'Parameter utama belum diatur')
    sample = PanelInput(id='template-main', title=config['name'], kind=config['kind'],
                        metric_codes=codes, w=12, h=2)
    panels = _validated(db, [sample], ctx.id)
    item = DashboardLayout(name=config['name'], description='Dashboard dari template BerauLoad',
                           scope='personal', owner_id=u.id, panels=panels, updated_by=u.id, unit_id=ctx.id)
    db.add(item)
    db.flush()
    record_revision(db, item, u.id)
    _audit(db, u, 'dashboard_from_template', item, {'template': key})
    db.commit()
    return _serial(item, db, ctx.id)
