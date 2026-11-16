"""Topology CRUD and read-only historical API. All writes require admin + CSRF."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import AuditLog, Metric, User, get_db
from ...security import current_user, require
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import metric_catalog, status_summary
from .data_service import hourly_data, day_series
from .links import validate_links, browse
from .models import TopologyDiagram
from .repository import (add_revision, compare_and_swap, diagram, list_diagrams,
                         references, revision, revision_list)
from .service import EMPTY_LAYOUT, TopologyError, string, validate_layout

router = APIRouter(prefix='/api/topology', tags=['Topologi Single Line'],
                   dependencies=[Depends(unit_context('read'))])


class CreateDiagram(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(default='', max_length=500)
    layout: dict | None = None


class UpdateDiagram(CreateDiagram):
    expected_version: int = Field(ge=1)


class RestoreDiagram(BaseModel):
    version: int = Field(ge=1)
    expected_version: int = Field(ge=1)


def _item(db, id, unit_id, allow_archived=False):
    record = diagram(db, id, unit_id)
    if record is None or (record.archived and not allow_archived):
        raise HTTPException(404, 'Diagram tidak ditemukan atau telah diarsipkan')
    return record


def _serialize(row):
    return {'id': row.id, 'name': row.name, 'description': row.description,
            'layout': row.layout, 'version': row.version, 'archived': row.archived,
            'updated_by': row.updated_by, 'updated_at': row.updated_at,
            'created_at': row.created_at}


def _layout(db, value, unit_id, source_id=None):
    assets, metrics, rules = references(db, unit_id)
    try:
        layout = validate_layout(value, assets, metrics, set(rules))
        validate_links(db, layout, unit_id, source_id)
        return layout
    except TopologyError as exc:
        raise HTTPException(422, str(exc)) from exc


def _names(name, description):
    try:
        string(name, 'Nama diagram', 150)
        string(description, 'Deskripsi diagram', 500, allow_empty=True)
    except TopologyError as exc:
        raise HTTPException(422, str(exc)) from exc


def _audit(db, actor, row, action, detail=None):
    db.add(AuditLog(user_id=actor.id, unit_id=row.unit_id, action=action,
                    target=f'topology:{row.id}', detail=detail or {}))


def _write_version(db, row, version, values, actor, action):
    if version != row.version or not compare_and_swap(db, row, version, values):
        db.rollback()
        raise HTTPException(409, 'Diagram sudah diubah pengguna lain, muat ulang')
    db.refresh(row)
    add_revision(db, row, actor.id)
    _audit(db, actor, row, action, {'version': row.version})
    db.commit()
    return _serialize(row)


@router.get('')
def list_topology(u: User = Depends(current_user), db: Session = Depends(get_db),
                  ctx:UnitContext=Depends(unit_context('read'))):
    return [_serialize(item) for item in list_diagrams(db, ctx.id)]


@router.get('/browse')
def browse_topology(u: User = Depends(current_user), db: Session = Depends(get_db),
                    ctx: UnitContext = Depends(unit_context('read'))):
    return browse(db, u, ctx.id)


@router.get('/link-targets')
def link_targets(u: User = Depends(current_user), db: Session = Depends(get_db),
                 ctx: UnitContext = Depends(unit_context('read'))):
    return browse(db, u, ctx.id, include_self=False)


@router.post('', status_code=201)
def create_topology(body: CreateDiagram, u: User = Depends(require('admin')),
                    db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('configure'))):
    _names(body.name, body.description)
    layout = _layout(db, body.layout if body.layout is not None else EMPTY_LAYOUT, ctx.id)
    row = TopologyDiagram(name=body.name, description=body.description,
                          layout=layout, version=1, updated_by=u.id, unit_id=ctx.id)
    db.add(row)
    db.flush()
    add_revision(db, row, u.id)
    _audit(db, u, row, 'topology_create', {'version': 1})
    db.commit()
    return _serialize(row)


@router.get('/{id}')
def get_topology(id: int, u: User = Depends(current_user),
                 db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    return _serialize(_item(db, id, ctx.id))


@router.put('/{id}')
def save_topology(id: int, body: UpdateDiagram, u: User = Depends(require('admin')),
                  db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('configure'))):
    row = _item(db, id, ctx.id)
    _names(body.name, body.description)
    if body.layout is None:
        raise HTTPException(422, 'Layout wajib diisi saat menyimpan')
    layout = _layout(db, body.layout, ctx.id, id)
    return _write_version(db, row, body.expected_version,
                          {'layout': layout, 'name': body.name,
                           'description': body.description, 'updated_by': u.id},
                          u, 'topology_update')


@router.post('/{id}/archive')
def archive_topology(id: int, u: User = Depends(require('admin')),
                     db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('configure'))):
    row = _item(db, id, ctx.id)
    return _write_version(db, row, row.version,
                          {'archived': True, 'updated_by': u.id},
                          u, 'topology_archive')


@router.get('/{id}/revisions')
def revisions(id: int, u: User = Depends(current_user),
              db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    _item(db, id, ctx.id, allow_archived=True)
    return [{'version': r.version, 'snapshot': r.snapshot,
             'updated_by': r.updated_by, 'created_at': r.created_at}
            for r in revision_list(db, id)]


@router.post('/{id}/restore-version')
def restore_topology(id: int, body: RestoreDiagram,
                     u: User = Depends(require('admin')), db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('configure'))):
    row = _item(db, id, ctx.id, allow_archived=True)
    past = revision(db, id, body.version)
    if past is None:
        raise HTTPException(404, 'Versi diagram tidak ditemukan')
    snap = past.snapshot
    _names(snap['name'], snap['description'])
    layout = _layout(db, snap['layout'], ctx.id, id)
    return _write_version(db, row, body.expected_version,
                          {'name': snap['name'], 'description': snap['description'],
                           'layout': layout, 'archived': False, 'updated_by': u.id},
                          u, 'topology_restore')


@router.get('/{id}/data')
def topology_hour(id: int, day: date, hour: int, u: User = Depends(current_user),
                  db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    if not 0 <= hour <= 23:
        raise HTTPException(422, 'Jam harus antara 0 dan 23')
    row = _item(db, id, ctx.id)
    _assets, _active_metrics, rules = references(db, ctx.id)
    # Inactive historical metrics may remain visible in an old saved layout.
    metrics = {code: (m.unit, m.asset_id) for code, m in metric_catalog(db, ctx.id, include_inactive=True).items()}
    result = hourly_data(db, row.layout, day, hour, metrics, rules, ctx.id)
    result['source_status'] = status_summary(db, ctx.id,
        {c for b in row.layout['boxes'] for c in b['metric_codes']}, day)
    return result


@router.get('/{id}/series')
def topology_series(id: int, day: date, u: User = Depends(current_user),
                    db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    row = _item(db, id, ctx.id)
    metrics = {code: (m.unit, m.asset_id) for code, m in metric_catalog(db, ctx.id, include_inactive=True).items()}
    result = day_series(db, row.layout, day, metrics, ctx.id)
    result['source_status'] = status_summary(db, ctx.id,
        {c for b in row.layout['boxes'] for c in b['metric_codes']}, day)
    return result
