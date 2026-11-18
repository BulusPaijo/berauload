"""Paged visit listing, atomic bulk save and verifier-only workflows."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from datetime import date
from .models import SubstationSession
from ...db import get_db, AuditLog, now
from ..org_units.context import UnitContext, unit_context
from .common import audit, child_ids, data_units, dump, ensure_owner, page_query, require_verifier
from .models import Substation, SubstationMeasurement, SubstationValue
from .schemas import VisitForm, BulkVisits, BulkAction
from .visits_service import detail, save_visit
from .calculation_service import get_results, save_results
from .models_calc import GarduCalcValue, GarduCalcMatch, GarduCalcMark
from .visit_history import header, history, latest_changed_cells, list_labels

router = APIRouter(prefix='/api/substations', tags=['Substation Measurements'])


@router.get('/measurements')
def list_visits(start: date | None = None, end: date | None = None,
                session: str | None = None, feeder_id: int | None = None,
                substation_id: int | None = None, state: str | None = None,
                technician: str | None = None, unit_id: int | None = None,
                page: int = 1, page_size: int = 50, sort: str = 'measured_on',
                desc: bool = True,
                ctx: UnitContext = Depends(unit_context('read')),
                db: Session = Depends(get_db)):
    if start and end and start > end:
        raise HTTPException(422, 'Tanggal mulai harus sebelum tanggal akhir')
    allowed = child_ids(db, ctx)
    if unit_id and unit_id not in allowed:
        raise HTTPException(404, 'Unit tidak ditemukan')
    query = db.query(SubstationMeasurement).filter(
        SubstationMeasurement.unit_id.in_([unit_id] if unit_id else allowed))
    for key, value in (('session', session), ('substation_id', substation_id),
                       ('state', state), ('technician', technician)):
        if value is not None:
            query = query.filter(getattr(SubstationMeasurement, key) == value)
    if start:
        query = query.filter(SubstationMeasurement.measured_on >= start)
    if end:
        query = query.filter(SubstationMeasurement.measured_on <= end)
    if feeder_id is not None:
        query = query.filter(SubstationMeasurement.snapshot_feeder_id == feeder_id)
    sorts = ('measured_on', 'session', 'state', 'updated_at', 'substation_id')
    if sort not in sorts:
        raise HTTPException(422, 'Kolom sortir tidak dikenal')
    column = getattr(SubstationMeasurement, sort)
    result = page_query(query.order_by(column.desc() if desc else column.asc(),
                                       SubstationMeasurement.id.desc()), page, page_size)
    result['items'] = list_labels(db, result['items'])
    return result


@router.get('/measurements/grid')
def grid_visits(day: str, session: str, ids: str = '',
                ctx: UnitContext = Depends(unit_context('read')),
                db: Session = Depends(get_db)):
    """Batch grid read: one visit query and one value query, no N+1."""
    from datetime import date
    try:
        measured_on = date.fromisoformat(day)
        selected = [int(x) for x in ids.split(',') if x]
    except (ValueError, TypeError):
        raise HTTPException(422, 'Tanggal atau ID gardu tidak valid')
    if len(selected) > 200:
        raise HTTPException(422, 'Maksimal 200 gardu per halaman')
    allowed = child_ids(db, ctx)
    if not selected:
        return {'items': []}
    masters = db.query(Substation).filter(Substation.id.in_(selected),
                Substation.unit_id.in_(allowed)).all()
    visible = [m.id for m in masters]
    visits = db.query(SubstationMeasurement).filter(
        SubstationMeasurement.substation_id.in_(visible),
        SubstationMeasurement.measured_on == measured_on,
        SubstationMeasurement.session == session).all()
    visits_by_id = {row.id: row for row in visits}
    values = db.query(SubstationValue).filter(
        SubstationValue.measurement_id.in_(list(visits_by_id) or [-1])).all()
    by_visit = {}
    for value in values:
        by_visit.setdefault(value.measurement_id, []).append(dump(value))
    return {'items': [{**dump(v), 'values': by_visit.get(v.id, [])} for v in visits]}


def visible_visit(db, ctx, id):
    row = db.get(SubstationMeasurement, id)
    if not row or row.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Pengukuran tidak ditemukan')
    return row


@router.get('/measurements/{id}')
def get_visit(id: int, ctx: UnitContext = Depends(unit_context('read')),
              db: Session = Depends(get_db)):
    row = visible_visit(db, ctx, id)
    events = db.query(AuditLog).filter(AuditLog.target == str(id),
              AuditLog.action.like('substation_visit_%')).order_by(
              AuditLog.id.desc()).limit(100)
    entries = history(db, id)
    return {'measurement': detail(db, row), 'header': header(db, row),
            'calculated': get_results(db, row.id), 'history': entries,
            'changed_cells': latest_changed_cells(entries),
            'audit': [dump(v) for v in events]}


@router.get('/measurements/{id}/xlsx')
def visit_xlsx(id: int, ctx: UnitContext = Depends(unit_context('read')),
               db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from .visit_xlsx import build
    row = visible_visit(db, ctx, id)
    head = header(db, row)
    content = build(db, detail(db, row), head, get_results(db, row.id),
                    latest_changed_cells(history(db, id)))
    raw = f"pengukuran_{head['substation_code'] or id}_{row.measured_on}_{row.session}"
    name = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in raw) + '.xlsx'
    return Response(content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{name}"'})


@router.put('/measurements')
def put_visit(body: VisitForm, ctx: UnitContext = Depends(unit_context('write_data')),
              db: Session = Depends(get_db)):
    result = save_visit(db, ctx, body)
    db.commit()
    return result


@router.post('/measurements/bulk')
def bulk_visits(body: BulkVisits,
                ctx: UnitContext = Depends(unit_context('write_data')),
                db: Session = Depends(get_db)):
    from .calculation_service import prepare
    calc_prepared = prepare(db)
    results = []
    for index, item in enumerate(body.items):
        try:
            with db.begin_nested():
                result = save_visit(db, ctx, item, calc_prepared=calc_prepared)
            results.append({'index': index, **result})
        except IntegrityError:
            results.append({'index': index, 'status': 'conflict', 'reason': 'Kunci tanggal/sesi sudah terpakai'})
        except HTTPException as exc:
            results.append({'index': index, 'status': 'conflict' if exc.status_code == 409
                            else 'error', 'reason': exc.detail})
    db.commit()
    return {'results': results}


def execute_action(db, ctx, id, body):
    query = db.query(SubstationMeasurement).filter(SubstationMeasurement.id == id,
                                                    SubstationMeasurement.unit_id.in_(data_units(db, ctx)))
    if db.bind.dialect.name == 'postgresql':
        query = query.with_for_update()
    visit = query.first()
    if visit is None:
        raise HTTPException(404, 'Pengukuran tidak ditemukan pada unit ini')
    if body.action in ('verify', 'reopen'):
        require_verifier(ctx)
    if body.action == 'verify' and visit.state != 'draft':
        raise HTTPException(409, 'Hanya draft dapat diverifikasi')
    if body.action == 'reopen' and visit.state != 'verified':
        raise HTTPException(409, 'Hanya verified dapat dibuka kembali')
    if body.action == 'reopen' and not (body.reason or '').strip():
        raise HTTPException(422, 'Alasan buka kunci wajib diisi')
    if body.action in ('delete', 'update') and visit.state != 'draft':
        raise HTTPException(409, 'Pengukuran verified terkunci')
    before = detail(db, visit)
    if body.action == 'verify':
        visit.state, visit.verified_by, visit.verified_at = 'verified', ctx.actor.id, now()
    if body.action == 'reopen':
        visit.state, visit.verified_by, visit.verified_at = 'draft', None, None
    if body.action == 'update':
        allowed = {'measured_on', 'session', 'technician', 'measured_at'}
        for key, value in (body.changes or {}).items():
            if key not in allowed:
                raise HTTPException(422, f'Kolom {key} tidak boleh diubah massal')
            if key == 'measured_on':
                try: value = date.fromisoformat(str(value))
                except ValueError: raise HTTPException(422, 'Tanggal wajib YYYY-MM-DD')
            if key == 'session' and not db.query(SubstationSession).filter_by(code=value, active=True).first():
                raise HTTPException(422, 'Sesi tidak aktif')
            setattr(visit, key, value)
    if body.action == 'delete':
        db.query(GarduCalcValue).filter_by(measurement_id=visit.id).delete()
        db.query(GarduCalcMatch).filter_by(measurement_id=visit.id).delete()
        db.query(GarduCalcMark).filter_by(measurement_id=visit.id).delete()
        db.query(SubstationValue).filter_by(measurement_id=visit.id).delete()
        db.delete(visit)
    else:
        visit.revision += 1
        visit.updated_by, visit.updated_at = ctx.actor.id, now()
        if body.action == 'update':
            save_results(db, visit)
    audit(db, ctx, 'substation_visit_' + body.action, id, before,
          None if body.action == 'delete' else detail(db, visit), reason=body.reason)
    return {'id': id, 'status': body.action}


@router.post('/measurements/actions')
def bulk_actions(body: BulkAction,
                 ctx: UnitContext = Depends(unit_context('write_data')),
                 db: Session = Depends(get_db)):
    if body.action in ('verify', 'reopen'):
        require_verifier(ctx)
    results = []
    for id in body.ids:
        try:
            with db.begin_nested():
                result = execute_action(db, ctx, id, body)
            results.append(result)
        except IntegrityError:
            results.append({'id': id, 'status': 'error', 'reason': 'Tanggal/sesi sudah dipakai'})
        except HTTPException as exc:
            results.append({'id': id, 'status': 'error', 'reason': exc.detail})
    db.commit()
    return {'results': results}
