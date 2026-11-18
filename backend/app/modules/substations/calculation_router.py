"""Stage 9b global definition API and read-only derived measurement API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import get_db
from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo
from ..org_units.context import unit_context, UnitContext
from .common import child_ids, dump, require_admin
from .models import SubstationMeasurement, Substation
from .models_calc import (GarduCalcColumn, GarduCalcRule, GarduCalcConstant,
                          GarduCalcHistory, GarduCalcSettings, GarduCalcMatch)
from .calculation_admin import MODELS, persist, restore_default, restore_all_defaults, update_settings, reorder_rules
from .calculation_rules import inspect_expression, order_columns
from .calculation_service import (compute, get_results, recalc_batch,
                                  recalc_status, latest_visits)

router = APIRouter(prefix='/api/substations/calculations', tags=['Gardu Calculations'])
_SQLITE_RECALC_LOCK = Lock()


class ExpressionBody(BaseModel):
    expression: str = Field(min_length=1, max_length=500)
    kind: str = 'column'


class TestBody(ExpressionBody):
    measurement_id: int
    code: str | None = None
    empty_mode: str = 'batal'


class PreviewBody(ExpressionBody):
    code: str
    empty_mode: str = 'batal'
    limit: int = Field(default=100, ge=1, le=150)


class StaleBody(BaseModel):
    stale_days: int = Field(ge=1, le=3650)


def authorized(db, ctx, identifier):
    visit = db.get(SubstationMeasurement, identifier)
    if not visit or visit.unit_id not in child_ids(db, ctx):
        raise HTTPException(404, 'Pengukuran tidak ditemukan')
    return visit


@router.get('/definitions')
def list_calculations(db: Session = Depends(get_db),
                      ctx: UnitContext = Depends(unit_context('read'))):
    cols = db.query(GarduCalcColumn).order_by(GarduCalcColumn.display_order).all()
    rules = db.query(GarduCalcRule).order_by(GarduCalcRule.display_order).all()
    constants = db.query(GarduCalcConstant).order_by(GarduCalcConstant.code).all()
    settings = db.get(GarduCalcSettings, 1)
    # Counts are based on the latest measurement per gardu, not all historical visits.
    ranked = db.query(SubstationMeasurement.id.label('id'), func.row_number().over(
        partition_by=SubstationMeasurement.substation_id,
        order_by=(SubstationMeasurement.measured_on.desc(),
                  SubstationMeasurement.id.desc())).label('rank')).filter(
                  SubstationMeasurement.unit_id.in_(child_ids(db, ctx))).subquery()
    latest = db.query(ranked.c.id).filter(ranked.c.rank == 1).subquery()
    totals = dict(db.query(GarduCalcMatch.rule_id, func.count(GarduCalcMatch.id)).join(
        latest, GarduCalcMatch.measurement_id == latest.c.id).group_by(
        GarduCalcMatch.rule_id).all())
    return {'columns': [dump(v) for v in cols],
            'rules': [{**dump(v), 'gardu_count': totals.get(v.id, 0)} for v in rules],
            'constants': [dump(v) for v in constants],
            'settings': dump(settings) if settings else None,
            'provisional': True,
            'warning': 'Ambang bawaan sementara; perlu konfirmasi pemilik proyek'}


@router.get('/stale')
def stale_substations(limit: int = 100, db: Session = Depends(get_db),
                       ctx: UnitContext = Depends(unit_context('read'))):
    if not 1 <= limit <= 200: raise HTTPException(422, 'Batas 1–200 gardu')
    settings = db.get(GarduCalcSettings, 1)
    threshold = settings.stale_days if settings else 180
    today = datetime.now(ZoneInfo('Asia/Makassar')).date()
    last = db.query(SubstationMeasurement.substation_id.label('id'),
                    func.max(SubstationMeasurement.measured_on).label('last')).group_by(
                    SubstationMeasurement.substation_id).subquery()
    rows = db.query(Substation, last.c.last).outerjoin(last, Substation.id==last.c.id
        ).filter(Substation.unit_id.in_(child_ids(db,ctx)),Substation.active.is_(True))
    overdue = []
    for gardu,last_date in rows:
        age = (today-last_date).days if last_date else None
        if age is None or age > threshold:
            overdue.append({'id':gardu.id,'code':gardu.code,
                            'last_measured':last_date.isoformat() if last_date else None,
                            'age_days':age})
    return {'as_of':today.isoformat(),'threshold_days':threshold,
            'total':len(overdue),'items':overdue[:limit], 'truncated':len(overdue)>limit}


@router.post('/check')
def check_formula(body: ExpressionBody,
                  ctx: UnitContext = Depends(unit_context('read')),
                  db: Session = Depends(get_db)):
    if body.kind not in ('column', 'rule'):
        raise HTTPException(422, 'Jenis periksa harus column atau rule')
    return {'valid': True, **inspect_expression(body.expression, db,
                                                rule=body.kind == 'rule')}


@router.get('/history/{kind}/{code}')
def change_history(kind: str, code: str,
                   db: Session = Depends(get_db),
                   ctx: UnitContext = Depends(unit_context('read'))):
    if kind not in MODELS: raise HTTPException(404, 'Jenis tidak ditemukan')
    rows = db.query(GarduCalcHistory).filter_by(kind=kind, code=code).order_by(
        GarduCalcHistory.id.desc()).limit(100).all()
    return [dump(row) for row in rows]


@router.post('/test')
def test_formula(body: TestBody, db: Session = Depends(get_db),
                 ctx: UnitContext = Depends(unit_context('read'))):
    visit = authorized(db, ctx, body.measurement_id)
    code = body.code or '__uji_rumus__'
    current = db.query(GarduCalcColumn).filter_by(code=code).first()
    if body.kind != 'column': raise HTTPException(422, 'Uji angka hanya untuk kolom')
    inspect_expression(body.expression, db)
    original = get_results(db, visit.id)
    draft = {'kind': 'column', 'code':code, 'id':current.id if current else None,
             'name': current.name if current else 'Uji',
             'unit': current.unit if current else '—',
             'decimals': current.decimals if current else 2,
             'expression': body.expression, 'empty_mode':body.empty_mode, 'active':True}
    order_columns(db, draft)
    projected = compute(db, visit, draft)
    changed = next((v for v in projected['columns'] if v['code'] == code), None)
    old = next((v for v in original['columns'] if v['code'] == code), None)
    a, b = old['value'] if old else None, changed['value'] if changed else None
    return {'current': a, 'draft': b, 'difference': b-a if a is not None and b is not None else None,
            'missing': changed['missing'] if changed else [], 'result': changed,
            'stale': original['stale']}


@router.post('/preview')
def preview_impact(body: PreviewBody,
                   db: Session = Depends(get_db),
                   ctx: UnitContext = Depends(unit_context('read'))):
    require_admin(ctx)
    if body.kind != 'column': raise HTTPException(422, 'Pratinjau saat ini untuk kolom hitung')
    inspect_expression(body.expression, db)
    current = db.query(GarduCalcColumn).filter_by(code=body.code).first()
    if current is None: raise HTTPException(404, 'Kolom tidak ditemukan')
    draft = {**dump(current), 'kind':'column', 'expression':body.expression,
             'empty_mode':body.empty_mode}
    order_columns(db, draft)
    visits, truncated = latest_visits(db, body.limit, 3000)
    changed_rules, sample = {}, []
    for visit in visits:
        base, candidate = compute(db, visit), compute(db, visit, draft)
        prior = {v['code'] for v in base['matches']}
        after = {v['code'] for v in candidate['matches']}
        for code in prior ^ after:
            item = changed_rules.setdefault(code, {'added':0,'removed':0})
            item['added' if code in after else 'removed'] += 1
        previous = next((v['value'] for v in base['columns'] if v['code']==body.code), None)
        future = next((v['value'] for v in candidate['columns'] if v['code']==body.code), None)
        if len(sample)<10:
            sample.append({'measurement_id':visit.id, 'substation_id':visit.substation_id,
                           'current':previous, 'draft':future})
    return {'scanned':len(visits), 'truncated':truncated,
            'message': ('Tidak ada perubahan pada '+str(len(visits))+
                        ' pengukuran terakhir' if not changed_rules else None),
            'warning':'Pratinjau dibatasi; bukan seluruh gardu' if truncated else None,
            'rule_changes':changed_rules, 'sample':sample,
            'writes':0}


@router.get('/recalculate/status')
def status(db: Session = Depends(get_db),
           ctx: UnitContext = Depends(unit_context('read'))):
    return recalc_status(db)


@router.post('/recalculate')
def recalculate(limit: int = 100, db: Session = Depends(get_db),
                ctx: UnitContext = Depends(unit_context('read'))):
    require_admin(ctx)
    if not 1 <= limit <= 200: raise HTTPException(422, 'Batch harus 1–200')
    sqlite = db.bind.dialect.name == 'sqlite'
    if sqlite and not _SQLITE_RECALC_LOCK.acquire(blocking=False):
        return {'busy':True,'processed':0,**recalc_status(db)}
    try:
        result = recalc_batch(db, limit)
        db.commit()
        return result
    finally:
        if sqlite: _SQLITE_RECALC_LOCK.release()


@router.post('/rules/reorder')
def reorder_rule_list(body:dict,db:Session=Depends(get_db),
                      ctx:UnitContext=Depends(unit_context('read'))):
    result=reorder_rules(db,ctx,body.get('kind'),body.get('codes'))
    db.commit()
    return result


@router.post('/settings')
def set_settings(body: StaleBody,
                 db: Session = Depends(get_db),
                 ctx: UnitContext = Depends(unit_context('read'))):
    result = update_settings(db, ctx, body.stale_days)
    db.commit()
    return result


@router.get('/measurements/{id}/results')
def measurement_results(id: int, db: Session = Depends(get_db),
                        ctx: UnitContext = Depends(unit_context('read'))):
    authorized(db, ctx, id)
    return get_results(db, id)


@router.post('/columns/restore-all')
def restore_all(db: Session = Depends(get_db),
                ctx: UnitContext = Depends(unit_context('read'))):
    result = restore_all_defaults(db, ctx)
    db.commit()
    return result


@router.post('/columns/{id}/restore')
def restore_column(id: int, db: Session = Depends(get_db),
                   ctx: UnitContext = Depends(unit_context('read'))):
    response = restore_default(db, ctx, id)
    db.commit()
    return response


@router.post('/{kind}')
def create_item(kind: str, body: dict,
                db: Session = Depends(get_db),
                ctx: UnitContext = Depends(unit_context('read'))):
    response = persist(db, ctx, kind, body)
    db.commit()
    return response


@router.patch('/{kind}/{id}')
def edit_item(kind: str, id: int, body: dict,
              db: Session = Depends(get_db),
              ctx: UnitContext = Depends(unit_context('read'))):
    response = persist(db, ctx, kind, body, id)
    db.commit()
    return response
