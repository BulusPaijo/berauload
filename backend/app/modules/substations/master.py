"""Paged master management, feeders, editable transformer metadata and history."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .common import (master_context, audit, check_code, check_master, child_ids, data_units, dump,
                     ensure_data_unit, ensure_owner, family_code_taken, master_manager,
                     page_query, require_admin, require_master_manager, TRAFO_FIELDS)
from .followup_models import GarduFollowup
from .models import (Substation, SubstationFeeder, SubstationMeasurement,
                     SubstationMasterHistory, SubstationValue)
from .schemas import (MasterForm, MasterPatch, BulkMasterPatch,
                      FeederForm, FeederPatch)

router = APIRouter(prefix='/api/substations', tags=['Substations'])


def reduce_line_affected(db, substation_id, target):
    """Count nonempty historic line readings; never mutate the snapshots."""
    return db.query(func.count(SubstationValue.id)).join(
        SubstationMeasurement, SubstationMeasurement.id == SubstationValue.measurement_id
    ).filter(SubstationMeasurement.substation_id == substation_id,
             SubstationValue.line_no > target,
             or_(SubstationValue.value.is_not(None),
                 SubstationValue.flag.is_not(None))).scalar() or 0


def move_unit(db, ctx, row, target):
    """9d-4: move a gardu inside one ULP family; its history and follow-ups follow it."""
    ensure_data_unit(db, ctx, target)
    if family_code_taken(db, target, row.code, row.id):
        raise HTTPException(409, 'Kode gardu sudah dipakai di unit tujuan')
    db.query(SubstationMeasurement).filter_by(substation_id=row.id).update(
        {SubstationMeasurement.unit_id: target}, synchronize_session=False)
    db.query(GarduFollowup).filter_by(substation_id=row.id).update(
        {GarduFollowup.unit_id: target}, synchronize_session=False)


def update_master(db, ctx, row, changes, effective_on=None):
    ensure_data_unit(db, ctx, row.unit_id)
    require_master_manager(db, ctx)
    confirm = changes.pop('confirm_line_reduction', False)
    before = dump(row)
    target_unit = changes.get('unit_id')
    if target_unit is None:
        changes.pop('unit_id', None)
    elif target_unit != row.unit_id:
        move_unit(db, ctx, row, target_unit)
        if 'feeder_id' not in changes and row.feeder_id is not None:
            check_master(db, target_unit, {'feeder_id': row.feeder_id})
    else:
        changes.pop('unit_id')
    if 'code' in changes and changes['code'] is None:
        raise HTTPException(422, 'Kode gardu tidak boleh kosong')
    if 'code' in changes and changes['code'] != row.code:
        if db.query(SubstationMeasurement.id).filter_by(substation_id=row.id).first():
            raise HTTPException(409, 'Kode gardu permanen setelah ada pengukuran')
        if family_code_taken(db, changes.get('unit_id', row.unit_id), changes['code'], row.id):
            raise HTTPException(409, 'Kode gardu sudah dipakai')
    check_master(db, changes.get('unit_id', row.unit_id), changes)
    target = changes.get('line_count')
    if target is not None and target < row.line_count and not confirm:
        affected = reduce_line_affected(db, row.id, target)
        if affected:
            raise HTTPException(409, {'code': 'LINE_REDUCTION_CONFIRM_REQUIRED',
                'message': 'Pengurangan jurusan membutuhkan konfirmasi',
                'affected_values': affected})
    for key, value in changes.items():
        setattr(row, key, value)
    db.flush()
    after = dump(row)
    delta = {key: {'from': before[key], 'to': after[key]}
             for key in changes if before[key] != after[key]}
    if delta:
        row.updated_by = ctx.actor.id
        db.add(SubstationMasterHistory(substation_id=row.id,
               effective_on=effective_on or date.today(), changed_by=ctx.actor.id,
               changes=delta))
        audit(db, ctx, 'substation_master_update', row.code, before, after)
    return bool(delta)


def commit_unique(db, message):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, message) from exc


@router.get('/feeders')
def feeders(ctx: UnitContext = Depends(unit_context('read')),
            db: Session = Depends(get_db)):
    from .common import feeder_units
    units = set(child_ids(db, ctx)) | set(feeder_units(db, ctx.id))
    return [dump(f) for f in db.query(SubstationFeeder).filter(
        SubstationFeeder.unit_id.in_(units)).order_by(
        SubstationFeeder.unit_id, SubstationFeeder.display_order).all()]


def feeder_manager(db, ctx):
    """Feeders belong to the ULP: managed there by its verifier, or anywhere by global admin."""
    ensure_owner(ctx, ctx.id)
    require_master_manager(db, ctx)
    if not ctx.superadmin and ctx.unit.level != 'ulp':
        raise HTTPException(403, 'Penyulang diatur di tingkat ULP')


@router.post('/feeders')
def add_feeder(body: FeederForm, ctx: UnitContext = Depends(master_context()),
               db: Session = Depends(get_db)):
    feeder_manager(db, ctx)
    check_code(body.code)
    if db.query(SubstationFeeder.id).filter_by(unit_id=ctx.id, code=body.code).first():
        raise HTTPException(409, 'Kode penyulang telah dipakai pada unit ini')
    row = SubstationFeeder(unit_id=ctx.id, **body.model_dump())
    try:
        db.add(row); db.flush()
        audit(db, ctx, 'substation_feeder_create', row.code, after=dump(row))
        commit_unique(db, 'Kode penyulang sudah dipakai')
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode penyulang sudah dipakai') from exc
    return dump(row)


@router.patch('/feeders/{feeder_id}')
def edit_feeder(feeder_id: int, body: FeederPatch,
                ctx: UnitContext = Depends(master_context()),
                db: Session = Depends(get_db)):
    feeder_manager(db, ctx)
    row = db.get(SubstationFeeder, feeder_id)
    if row is None or row.unit_id != ctx.id:
        raise HTTPException(404, 'Penyulang tidak ditemukan')
    data = body.model_dump(exclude_unset=True)
    if 'code' in data:
        if data['code'] is None:
            raise HTTPException(422, 'Kode penyulang tidak boleh kosong')
        check_code(data['code'])
        if data.pop('code') != row.code:
            raise HTTPException(409, 'Kode penyulang permanen dan tidak dapat diganti')
    if data.get('active') is False and db.query(Substation.id).filter_by(
            feeder_id=feeder_id, active=True).first():
        raise HTTPException(409, 'Pindahkan gardu aktif ke penyulang lain sebelum arsip')
    before = dump(row)
    for key, value in data.items():
        setattr(row, key, value)
    if before != dump(row):
        audit(db, ctx, 'substation_feeder_update', row.code, before, dump(row))
    commit_unique(db, 'Kode penyulang sudah dipakai')
    return dump(row)


@router.post('/feeders/from-assets')
def from_assets(ctx: UnitContext = Depends(unit_context('write_data')),
                db: Session = Depends(get_db)):
    """Explicit opt-in import of feeder assets; no implicit creation."""
    from ...db import Asset
    feeder_manager(db, ctx)
    assets = db.query(Asset).filter_by(unit_id=ctx.id, active=True).all()
    present = {f.code for f in db.query(SubstationFeeder).filter_by(unit_id=ctx.id)}
    added = []
    for asset in assets:
        if 'FEEDER' not in (asset.kind or '').upper() or asset.code in present:
            continue
        check_code(asset.code)
        row = SubstationFeeder(unit_id=ctx.id, code=asset.code, name=asset.name)
        db.add(row); present.add(asset.code); added.append(asset.code)
    if added:
        audit(db, ctx, 'substation_feeder_import_assets', ctx.id, after=added)
    db.commit()
    return {'created': added}


@router.get('/master')
def list_master(q: str = '', feeder_id: int | None = None, unit_id: int | None = None,
                ownership: str | None = None, purpose: str | None = None,
                active: bool | None = True, sort: str = 'code', desc: bool = False,
                page: int = 1, page_size: int = 50,
                ctx: UnitContext = Depends(unit_context('read')),
                db: Session = Depends(get_db)):
    allowed = child_ids(db, ctx)
    if unit_id is not None and unit_id not in allowed:
        raise HTTPException(404, 'Unit tidak ditemukan')
    query = db.query(Substation).filter(Substation.unit_id.in_(
        [unit_id] if unit_id else allowed))
    if q:
        term = '%' + q.replace('%', '\\%').replace('_', '\\_') + '%'
        query = query.filter(or_(Substation.code.ilike(term),
                                 Substation.name.ilike(term)))
    for key, value in (('feeder_id', feeder_id), ('ownership', ownership),
                       ('purpose', purpose), ('active', active)):
        if value is not None:
            query = query.filter(getattr(Substation, key) == value)
    allowed_sort = ('code', 'name', 'power_kva', 'line_count', 'updated_at', 'feeder_id')
    if sort not in allowed_sort:
        raise HTTPException(422, 'Kolom sortir tidak dikenal')
    order = getattr(Substation, sort)
    result = page_query(query.order_by(order.desc() if desc else order.asc()), page, page_size)
    result['items'] = [dump(row) for row in result['items']]
    return result


@router.post('/master')
def add_master(body: MasterForm,
               ctx: UnitContext = Depends(master_context()),
               db: Session = Depends(get_db)):
    data = body.model_dump()
    target = data.pop('unit_id') or ctx.id
    ensure_data_unit(db, ctx, target)
    values = check_master(db, target, data)
    if family_code_taken(db, target, body.code):
        raise HTTPException(409, 'Kode gardu sudah ada pada ULP ini atau KP-nya')
    row = Substation(unit_id=target, **values, created_by=ctx.actor.id,
                     updated_by=ctx.actor.id)
    try:
        db.add(row); db.flush()
        audit(db, ctx, 'substation_master_create', row.code, after=dump(row))
        commit_unique(db, 'Kode gardu sudah dipakai')
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode gardu sudah dipakai') from exc
    return dump(row)


@router.get('/master/{id}')
def get_master(id: int, ctx: UnitContext = Depends(unit_context('read')),
               db: Session = Depends(get_db)):
    row = db.get(Substation, id)
    if row is None or row.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan')
    return {'master': dump(row), 'history': [dump(h) for h in db.query(
        SubstationMasterHistory).filter_by(substation_id=id).order_by(
        SubstationMasterHistory.id.desc()).limit(100)]}


@router.patch('/master/bulk')
def bulk_master(body: BulkMasterPatch,
                ctx: UnitContext = Depends(master_context()),
                db: Session = Depends(get_db)):
    allowed = data_units(db, ctx)
    changes = body.changes.model_dump(exclude_unset=True)
    effective_on = changes.pop('effective_on', None)
    results = []
    for id in body.ids:
        try:
            with db.begin_nested():
                row = db.get(Substation, id)
                if row is None or row.unit_id not in allowed:
                    raise HTTPException(404, 'Gardu tidak ditemukan')
                changed = update_master(db, ctx, row, dict(changes), effective_on)
            results.append({'id': id, 'status': 'updated' if changed else 'unchanged'})
        except IntegrityError:
            results.append({'id': id, 'status': 'error', 'reason': 'Kode gardu sudah dipakai'})
        except HTTPException as exc:
            detail = exc.detail
            pending = isinstance(detail, dict) and detail.get('code') == 'LINE_REDUCTION_CONFIRM_REQUIRED'
            results.append({'id': id, 'status': 'needs_confirmation' if pending else 'error',
                            'reason': detail.get('message') if pending else detail,
                            'affected_values': detail.get('affected_values') if pending else 0})
    commit_unique(db, 'Kode gardu sudah dipakai')
    return {'results': results}


@router.patch('/master/{id}')
def edit_master(id: int, body: MasterPatch,
                ctx: UnitContext = Depends(master_context()),
                db: Session = Depends(get_db)):
    row = db.get(Substation, id)
    if row is None or row.unit_id not in data_units(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan')
    changes = body.model_dump(exclude_unset=True)
    effective_on = changes.pop('effective_on', None)
    try:
        changed = update_master(db, ctx, row, changes, effective_on)
        commit_unique(db, 'Kode gardu sudah dipakai')
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Kode gardu sudah dipakai') from exc
    return {'unchanged': not changed, 'master': dump(row)}


@router.get('/scope')
def scope(ctx: UnitContext = Depends(unit_context('read')), db: Session = Depends(get_db)):
    """9d-4: what the active context may write, so the UI can enable the right buttons."""
    from ..org_units.models import OrgUnit
    ids = data_units(db, ctx)
    units = db.query(OrgUnit).filter(OrgUnit.id.in_(ids)).order_by(OrgUnit.level.desc(), OrgUnit.display_order).all() if ids else []
    return {'data_unit_ids': ids, 'can_manage_master': master_manager(db, ctx) and bool(ids),
            'units': [{'id': u.id, 'name': u.name, 'level': u.level, 'parent_id': u.parent_id} for u in units]}
