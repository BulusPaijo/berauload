"""Administrative Engineering Rules API: draft, preview, activate and audit."""
from ..org_units.context import UnitContext, unit_context
from ..org_units.references import status_summary
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from ...db import AuditLog, User, get_db
from ...security import current_user, require
from ..formulas.engine import FormulaError
from ..units.models import UnitDefinition
from ..units.service import profile
from ..historical.repository import iter_readings
from .models import EngineeringRuleRevision
from .repository import add_rule, all_rules, find, find_revision, snapshots, units
from .service import RULE_FIELDS, evaluate_history, evaluate_sample, validate_rule

router = APIRouter(prefix='/api/engineering-rules', tags=['Engineering Rules'], dependencies=[Depends(unit_context('read'))])


class RuleInput(BaseModel):
    code: str = Field(min_length=2, max_length=90, pattern=r'^[a-z][a-z0-9_]*$')
    name: str = Field(min_length=2, max_length=180)
    expression: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=12)
    direction: str = 'below'
    warning_threshold: float
    critical_threshold: float
    reference_note: str = Field(min_length=8, max_length=500)
    effective_from: date

    @field_validator('name')
    @classmethod
    def safe_name(cls, name):
        if name.lstrip().startswith(('=', '+', '-', '@')):
            raise ValueError('Nama tidak boleh diawali ekspresi spreadsheet')
        return name


class SampleRequest(RuleInput):
    samples: dict[str, float] = Field(default_factory=dict)


class Decision(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class RuleRevisionRequest(RuleInput):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


def _get(db, id, unit_id):
    item = find(db, id, unit_id)
    if item is None:
        raise HTTPException(404, 'Aturan teknis tidak ditemukan')
    return item


def _serialize(item):
    return {**{field: getattr(item, field) for field in RULE_FIELDS},
            'id': item.id, 'version': item.version, 'status': item.status}


def _validate(spec, db, unit_id, include_inactive=False):
    try:
        return validate_rule(spec, units(db, include_inactive=include_inactive, unit_id=unit_id),
                             profile(db.query(UnitDefinition).all()))
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc


def _audit(db, user, item, action, detail):
    db.add(AuditLog(user_id=user.id, unit_id=item.unit_id, action=action, target=item.code, detail=detail))


@router.get('')
def list_rules(u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    return [_serialize(item) for item in all_rules(db, ctx.id) if item.status == 'active' or u.role == 'admin']


@router.post('/preview')
def preview(body: SampleRequest, u: User = Depends(require('admin')),
            db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    spec = body.model_dump(exclude={'samples'})
    _validate(spec, db, ctx.id)
    result = evaluate_sample(spec, body.samples, units(db, unit_id=ctx.id),
                             profile(db.query(UnitDefinition).all()))
    return {'result': result, 'advisory_only': True}


@router.post('', status_code=201)
def create(body: RuleInput, u: User = Depends(require('admin')),
           db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    spec = body.model_dump()
    refs = _validate(spec, db, ctx.id)
    from .models import EngineeringRule
    if db.query(EngineeringRule.id).filter_by(code=body.code).first():
        raise HTTPException(409, 'Kode aturan sudah ada')
    item = add_rule(db, spec, u.id, ctx.id)
    _audit(db, u, item, 'engineering_rule_create', {'version': 1, 'references': sorted(refs),
                                                   'reference_note': body.reference_note})
    db.commit()
    return _serialize(item)


@router.post('/{rule_id}/revisions', status_code=201)
def revise(rule_id: int, body: RuleRevisionRequest, u: User = Depends(require('admin')),
           db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _get(db, rule_id, ctx.id)
    if item.status == 'archived':
        raise HTTPException(409, 'Aturan diarsipkan')
    if body.code != item.code:
        raise HTTPException(422, 'Kode aturan tidak boleh diubah')
    if body.expected_version != item.version:
        raise HTTPException(409, 'Versi sudah berubah, muat ulang')
    spec = body.model_dump(exclude={'reason', 'expected_version'})
    refs = _validate(spec, db, ctx.id, include_inactive=True)
    item.version += 1
    for field in RULE_FIELDS:
        setattr(item, field, spec[field])
    item.status = 'draft'  # Changed rule must be explicitly reapproved.
    snapshot = {k: spec[k].isoformat() if k == 'effective_from' else spec[k] for k in RULE_FIELDS}
    db.add(EngineeringRuleRevision(rule_id=item.id, version=item.version,
                                   snapshot=snapshot, reason=body.reason, created_by=u.id))
    _audit(db, u, item, 'engineering_rule_revision', {'version': item.version,
           'reason': body.reason, 'references': sorted(refs)})
    db.commit()
    return _serialize(item)


@router.post('/{rule_id}/activate')
def activate(rule_id: int, body: Decision, u: User = Depends(require('admin')),
             db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _get(db, rule_id, ctx.id)
    if item.status != 'draft':
        raise HTTPException(409, 'Hanya draft yang dapat diaktifkan')
    _validate({field: getattr(item, field) for field in RULE_FIELDS}, db, ctx.id, include_inactive=True)
    item.status = 'active'
    _audit(db, u, item, 'engineering_rule_activate', {
        'version': item.version, 'reason': body.reason,
        'effective_from': item.effective_from.isoformat()})
    db.commit()
    return _serialize(item)


@router.post('/{rule_id}/archive')
def archive(rule_id: int, body: Decision, u: User = Depends(require('admin')),
            db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('configure'))):
    item = _get(db, rule_id, ctx.id)
    if item.status == 'archived':
        raise HTTPException(409, 'Sudah diarsipkan')
    item.status = 'archived'
    _audit(db, u, item, 'engineering_rule_archive', {'version': item.version, 'reason': body.reason})
    db.commit()
    return _serialize(item)


@router.get('/{rule_id}/revisions')
def history_versions(rule_id: int, u: User = Depends(current_user),
                     db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    _get(db, rule_id, ctx.id)
    return [{'version': r.version, 'snapshot': r.snapshot, 'reason': r.reason,
             'created_at': r.created_at} for r in snapshots(db, rule_id)]


@router.get('/{rule_id}/history')
def history(rule_id: int, start: date, end: date, version: int | None = None,
            u: User = Depends(current_user), db: Session = Depends(get_db), ctx:UnitContext=Depends(unit_context('read'))):
    item = _get(db, rule_id, ctx.id)
    if not start <= end or (end - start).days > 365:
        raise HTTPException(422, 'Rentang evaluasi maksimal 366 hari')
    if version is None:
        if item.status != 'active':
            raise HTTPException(409, 'Aturan belum aktif; tidak dapat mengevaluasi histori')
        spec = {field: getattr(item, field) for field in RULE_FIELDS}
        selected_version = item.version
    else:
        revision = find_revision(db, rule_id, version)
        if revision is None:
            raise HTTPException(404, 'Versi aturan tidak ditemukan')
        spec = {**revision.snapshot, 'effective_from': date.fromisoformat(revision.snapshot['effective_from'])}
        selected_version = revision.version
    if start < spec['effective_from']:
        raise HTTPException(422, 'Tanggal awal sebelum tanggal berlaku rule')
    refs = _validate(spec, db, ctx.id, include_inactive=True)
    result = evaluate_history(spec, iter_readings(db, refs, start, end, ctx.id), start, end,
                              units(db, include_inactive=True, unit_id=ctx.id), profile(db.query(UnitDefinition).all()))
    return {'rule': _serialize(item), 'evaluated_version': selected_version,
            'evaluated_unit': spec['unit'], 'evaluated_name': spec['name'],
            'source_status': status_summary(db, ctx.id, refs, end), **result}
