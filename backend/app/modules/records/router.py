"""Unit-isolated historical records and status transitions (Stage 4a)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import User, Metric, get_db
from ..unit_references.models import UnitSourceChange
from ..unit_references.recalculation import refresh_reopened_day
from ..org_units.references import status_summary
from ..org_units.context import UnitContext, unit_context
from ..org_units.models import OrgUnit
from ..formulas.repository import list_formulas
from ..formulas.engine import parse_formula
from ..org_units.roles import metric_for_role, SYSTEM_LOAD
from .service import day_status, day_readings, transition, unit_children, tree_eligibility, day_state

router = APIRouter(prefix='/api', tags=['Records'])


@router.get('/records/day')
def day_records(day: date, ctx: UnitContext = Depends(unit_context('read')),
                db: Session = Depends(get_db)):
    readings, sources = day_readings(db, day, ctx.id)
    if ctx.unit.level == 'up3':
        refs = {ref for definition, metric in list_formulas(db)
                if metric.unit_id == ctx.id
                for ref in parse_formula(definition.expression)[1]}
        return {'date': day.isoformat(), 'status': None,
                'filled_hours': len(readings), 'configured': bool(refs),
                'system_load_hours': None,
                'source_status': status_summary(db, ctx.id, refs, day),
                'hours': [{'hour': h, 'values': readings.get(h, {}),
                           'sources': sources.get(h, {})} for h in range(24)]}

    main = metric_for_role(db, ctx.id, SYSTEM_LOAD)
    count = sum(main.code in vals for vals in readings.values()) if main else None
    return {'date': day.isoformat(), 'status': day_status(db, day, ctx.id),
            'filled_hours': len(readings), 'configured': bool(main),
            'system_load_hours': count,
            'hours': [{'hour': h, 'values': readings.get(h, {}),
                       'sources': sources.get(h, {})} for h in range(24)]}


class StatusRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    confirm_draft_sources: bool = False




def _draft_kps(db, ctx, day):
    if ctx.unit.level != 'ulp':
        return []
    return [u for u in db.query(OrgUnit).filter_by(
        parent_id=ctx.id, level='kp', active=True).all()
        if day_status(db, day, u.id) == 'draft']

def _check_finalize_sources(db, ctx, day, body):
    pending = _draft_kps(db, ctx, day)
    if pending and not body.confirm_draft_sources:
        raise HTTPException(409, {'message': 'KP masih draft; konfirmasi diperlukan',
                                  'draft_units': [{'id': u.id, 'name': u.name} for u in pending]})
    return [u.id for u in pending]

def _change(day, body, ctx, db, action):
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'UP3 tidak memiliki status hari')
    pending = _check_finalize_sources(db, ctx, day, body) if action == 'finalize' else []
    result = transition(db, ctx, day, action, body.reason)
    if pending:
        from ...db import AuditLog
        db.add(AuditLog(unit_id=ctx.id, user_id=ctx.actor.id,
                        action='finalize_with_draft_sources', target=str(day),
                        detail={'unit_id': ctx.id, 'draft_kp_ids': pending,
                                'actor_role': 'admin_global' if ctx.superadmin else 'verifier'}))
    if action == 'reopen':
        result['refreshed_hours'] = refresh_reopened_day(db, ctx.id, day)
    db.commit()
    return result


@router.post('/days/{day}/verify')
def verify(day: date, body: StatusRequest,
           ctx: UnitContext = Depends(unit_context('write_data')),
           db: Session = Depends(get_db)):
    return _change(day, body, ctx, db, 'verify')


@router.post('/days/{day}/finalize')
def finalize(day: date, body: StatusRequest,
             ctx: UnitContext = Depends(unit_context('write_data')),
             db: Session = Depends(get_db)):
    return _change(day, body, ctx, db, 'finalize')


@router.post('/days/{day}/reopen')
def reopen(day: date, body: StatusRequest,
           ctx: UnitContext = Depends(unit_context('write_data')),
           db: Session = Depends(get_db)):
    return _change(day, body, ctx, db, 'reopen')


def _tree_plan(day, ctx, db, action):
    if not ctx.superadmin:
        ctx.role_for('verifier')
    plan = []
    for unit in unit_children(db, ctx.id):
        eligible, reason, final_status = tree_eligibility(db, day, unit, action)
        plan.append({'unit_id': unit.id, 'unit_code': unit.code,
                     'result': 'diproses' if eligible else 'dilewati',
                     'reason': reason, 'status': final_status})
    return plan


def _change_tree(day, body, ctx, db, action):
    plan = _tree_plan(day, ctx, db, action)
    if all(item['result'] == 'dilewati' for item in plan):
        summary = '; '.join(f"{item['unit_code']}: {item['reason']}" for item in plan)
        raise HTTPException(422, f'Tidak ada unit yang dapat diproses: {summary}')
    try:
        draft_by_unit = {}
        if action == 'finalize':
            for item in plan:
                if item['result'] != 'diproses':
                    continue
                unit = db.get(OrgUnit, item['unit_id'])
                if unit.level == 'ulp':
                    child = UnitContext(unit, ctx.actor, ctx.roles, ctx.superadmin)
                    pending = _check_finalize_sources(db, child, day, body)
                    if pending:
                        draft_by_unit[unit.id] = pending
        for item in plan:
            if item['result'] != 'diproses':
                continue
            unit = db.get(OrgUnit, item['unit_id'])
            child = UnitContext(unit, ctx.actor, ctx.roles, ctx.superadmin)
            result = transition(db, child, day, action, body.reason)
            item['status'] = result['status']
            if unit.id in draft_by_unit:
                from ...db import AuditLog
                db.add(AuditLog(user_id=ctx.actor.id, unit_id=unit.id,
                    action='finalize_with_draft_sources', target=str(day),
                    detail={'unit_id':unit.id,'draft_kp_ids':draft_by_unit[unit.id],
                        'actor_role':'admin_global' if ctx.superadmin else 'verifier'}))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'ok': True, 'date': day.isoformat(), 'units': plan, 'action': action}


@router.get('/days/{day}/status')
def status_detail(day: date, ctx: UnitContext = Depends(unit_context('read')),
                  db: Session = Depends(get_db)):
    if ctx.unit.level == 'up3':
        raise HTTPException(422, 'Pilih ULP atau KP')
    row = day_state(db, day, ctx.id)
    flags = (db.query(UnitSourceChange).filter_by(unit_id=ctx.id, day=day).all()
             if ctx.superadmin or 'verifier' in ctx.roles else [])
    return {'status': row.status if row else 'draft',
            'source_changed_after_final': bool(flags),
            'changed_sources': sorted({flag.source_unit_id for flag in flags}),
            'draft_kps': [{'id': u.id, 'name': u.name} for u in _draft_kps(db, ctx, day)],
            'verified_by': _actor(db, row.verified_by, day, ctx.id, 'day_verify') if row else None,
            'finalized_by': _actor(db, row.finalized_by, day, ctx.id, 'day_finalize') if row else None}


def _actor(db, user_id, day, unit_id, action):
    if user_id is None:
        return None
    user = db.get(User, user_id)
    from ...db import AuditLog
    audits = db.query(AuditLog).filter_by(user_id=user_id, action=action,
                                          target=str(day)).order_by(AuditLog.id.desc()).all()
    admin = any((a.detail or {}).get('unit_id') == unit_id and
                (a.detail or {}).get('actor_role') == 'admin_global' for a in audits)
    return {'id': user_id, 'name': user.display_name if user else f'ID {user_id}',
            'admin_global': admin}


@router.get('/days/{day}/tree-preview')
def tree_preview(day: date, action: str,
                 ctx: UnitContext = Depends(unit_context('read')),
                 db: Session = Depends(get_db)):
    if action not in ('verify', 'finalize'):
        raise HTTPException(422, 'Aksi tidak valid')
    if not ctx.superadmin:
        ctx.role_for('verifier')
    return {'date': day.isoformat(), 'action': action,
            'units': _tree_plan(day, ctx, db, action)}


@router.post('/days/{day}/verify-tree')
def verify_tree(day: date, body: StatusRequest,
                ctx: UnitContext = Depends(unit_context('write_data')),
                db: Session = Depends(get_db)):
    return _change_tree(day, body, ctx, db, 'verify')


@router.post('/days/{day}/finalize-tree')
def finalize_tree(day: date, body: StatusRequest,
                  ctx: UnitContext = Depends(unit_context('write_data')),
                  db: Session = Depends(get_db)):
    return _change_tree(day, body, ctx, db, 'finalize')
