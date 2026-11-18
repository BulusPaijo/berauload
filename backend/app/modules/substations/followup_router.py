"""Stage 9d-3 follow-ups: owner unit writes, parent reads, no delete (cancel only), audited."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .common import audit, child_ids, data_units, dump, require_admin
from .followup_models import PRIORITIES, STATUSES, GarduFollowup, GarduFollowupType
from .models import Substation, SubstationMeasurement
from .models_calc import GarduCalcMatch, GarduCalcRule

router = APIRouter(prefix='/api/substations/followups', tags=['Gardu Follow-up'])


class FollowupBody(BaseModel):
    substation_id: int | None = None
    measurement_id: int | None = None
    type_code: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, max_length=2000)
    priority: str = 'sedang'
    status: str = 'terbuka'
    assignee: str | None = Field(default=None, max_length=150)
    due_on: date | None = None
    expected_version: int | None = None


class BulkBody(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    status: str | None = None
    assignee: str | None = Field(default=None, max_length=150)


class TypeBody(BaseModel):
    code: str = Field(min_length=1, max_length=60, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(min_length=1, max_length=120)
    suggest_for: list[str] = Field(default_factory=list, max_length=30)
    active: bool = True


def check_values(db, body):
    if body.status not in STATUSES:
        raise HTTPException(422, 'Status tindak lanjut tidak dikenal')
    if body.priority not in PRIORITIES:
        raise HTTPException(422, 'Prioritas harus rendah, sedang, atau tinggi')
    if not db.query(GarduFollowupType.id).filter_by(code=body.type_code, active=True).first():
        raise HTTPException(422, 'Jenis tindak lanjut tidak dikenal')


def view(row, station=None, types=None):
    out = dump(row)
    if station is not None:
        out.update(code=station.code, name=station.name, feeder_id=station.feeder_id)
    if types is not None:
        out['type_name'] = types.get(row.type_code, row.type_code)
    return out


def type_names(db):
    return {t.code: t.name for t in db.query(GarduFollowupType)}


@router.get('/types')
def list_types(db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    return [dump(t) for t in db.query(GarduFollowupType).order_by(GarduFollowupType.display_order)]


@router.post('/types')
def save_type(body: TypeBody, db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    require_admin(ctx)
    row = db.query(GarduFollowupType).filter_by(code=body.code).first()
    before = dump(row) if row else None
    if row is None:
        order = db.query(GarduFollowupType).count()
        row = GarduFollowupType(code=body.code, display_order=order)
        db.add(row)
    row.name, row.suggest_for, row.active = body.name.strip(), body.suggest_for, body.active
    db.flush()
    audit(db, ctx, 'gardu_followup_type', row.id, before, dump(row))
    db.commit()
    return dump(row)


@router.get('')
def list_followups(status: list[str] = Query(default=[]), type_code: str = '', text: str = Query('', max_length=120),
                   substation_id: int | None = None, assignee: str = Query('', max_length=150),
                   page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                   db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    q = db.query(GarduFollowup, Substation).join(Substation, Substation.id == GarduFollowup.substation_id)\
        .filter(GarduFollowup.unit_id.in_(child_ids(db, ctx)))
    if status:
        bad = set(status) - set(STATUSES)
        if bad:
            raise HTTPException(422, 'Status tindak lanjut tidak dikenal')
        q = q.filter(GarduFollowup.status.in_(status))
    if type_code:
        q = q.filter(GarduFollowup.type_code == type_code)
    if substation_id:
        q = q.filter(GarduFollowup.substation_id == substation_id)
    if assignee:
        q = q.filter(GarduFollowup.assignee.ilike(f'%{assignee}%'))
    if text:
        like = f'%{text}%'
        q = q.filter(or_(Substation.code.ilike(like), Substation.name.ilike(like), GarduFollowup.note.ilike(like)))
    total = q.count()
    rows = q.order_by(GarduFollowup.status, GarduFollowup.due_on.is_(None), GarduFollowup.due_on,
                      GarduFollowup.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    names = type_names(db)
    counts = dict(db.query(GarduFollowup.status, func.count()).filter(
        GarduFollowup.unit_id.in_(child_ids(db, ctx))).group_by(GarduFollowup.status).all())
    return {'total': total, 'items': [view(f, s, names) for f, s in rows], 'counts': counts}


def owned(db, ctx, followup_id):
    row = db.get(GarduFollowup, followup_id)
    if row is None or row.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Tindak lanjut tidak ditemukan')
    if row.unit_id not in data_units(db, ctx):
        raise HTTPException(403, 'Hanya unit pemilik gardu atau ULP induknya yang dapat mengubah tindak lanjut')
    return row


@router.post('')
def create_followup(body: FollowupBody, db: Session = Depends(get_db),
                    ctx: UnitContext = Depends(unit_context('write_data'))):
    check_values(db, body)
    station = db.get(Substation, body.substation_id or 0)
    if station is None or station.unit_id not in data_units(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan pada unit aktif atau KP di bawahnya')
    if body.measurement_id:
        m = db.get(SubstationMeasurement, body.measurement_id)
        if m is None or m.substation_id != station.id:
            raise HTTPException(422, 'Pengukuran bukan milik gardu ini')
    row = GarduFollowup(unit_id=station.unit_id, substation_id=station.id, measurement_id=body.measurement_id,
                        type_code=body.type_code, note=(body.note or '').strip() or None, priority=body.priority,
                        status=body.status, assignee=(body.assignee or '').strip() or None, due_on=body.due_on,
                        created_by=ctx.actor.id, updated_by=ctx.actor.id)
    db.add(row)
    db.flush()
    audit(db, ctx, 'gardu_followup', row.id, None, dump(row))
    db.commit()
    return view(row, station, type_names(db))


@router.patch('/{followup_id}')
def update_followup(followup_id: int, body: FollowupBody, db: Session = Depends(get_db),
                    ctx: UnitContext = Depends(unit_context('write_data'))):
    row = owned(db, ctx, followup_id)
    check_values(db, body)
    if body.expected_version != row.version:
        raise HTTPException(409, 'Tindak lanjut sudah diubah pengguna lain. Muat ulang.')
    before = dump(row)
    row.type_code, row.note, row.priority = body.type_code, (body.note or '').strip() or None, body.priority
    row.status, row.assignee, row.due_on = body.status, (body.assignee or '').strip() or None, body.due_on
    row.version, row.updated_by = row.version + 1, ctx.actor.id
    db.flush()
    audit(db, ctx, 'gardu_followup', row.id, before, dump(row))
    db.commit()
    return view(row, db.get(Substation, row.substation_id), type_names(db))


@router.post('/bulk')
def bulk_update(body: BulkBody, db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('write_data'))):
    if body.status is None and body.assignee is None:
        raise HTTPException(422, 'Pilih status atau penanggung jawab')
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(422, 'Status tindak lanjut tidak dikenal')
    done, skipped, allowed = 0, [], data_units(db, ctx)
    for fid in body.ids:
        row = db.get(GarduFollowup, fid)
        if row is None or row.unit_id not in allowed:
            skipped.append(fid)
            continue
        before = dump(row)
        if body.status is not None:
            row.status = body.status
        if body.assignee is not None:
            row.assignee = body.assignee.strip() or None
        row.version, row.updated_by = row.version + 1, ctx.actor.id
        db.flush()
        audit(db, ctx, 'gardu_followup', row.id, before, dump(row), bulk=True)
        done += 1
    db.commit()
    return {'updated': done, 'skipped': skipped}


@router.get('/suggest/{substation_id}')
def suggest(substation_id: int, measurement_id: int | None = None, db: Session = Depends(get_db),
            ctx: UnitContext = Depends(unit_context('read'))):
    """Text suggestions only — never creates a follow-up by itself."""
    station = db.get(Substation, substation_id)
    if station is None or station.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Gardu tidak ditemukan')
    if not measurement_id:
        latest = db.query(SubstationMeasurement.id).filter_by(substation_id=substation_id)\
            .order_by(SubstationMeasurement.measured_on.desc(), SubstationMeasurement.id.desc()).first()
        measurement_id = latest[0] if latest else None
    codes = dict(db.query(GarduCalcRule.code, GarduCalcRule.name).join(
        GarduCalcMatch, GarduCalcMatch.rule_id == GarduCalcRule.id).filter(
        GarduCalcMatch.measurement_id == measurement_id).all()) if measurement_id else {}
    out = []
    for t in db.query(GarduFollowupType).filter_by(active=True).order_by(GarduFollowupType.display_order):
        reasons = [codes[c] for c in (t.suggest_for or []) if c in codes]
        if reasons:
            out.append({'type_code': t.code, 'name': t.name, 'because': reasons})
    return {'measurement_id': measurement_id, 'suggestions': out}
