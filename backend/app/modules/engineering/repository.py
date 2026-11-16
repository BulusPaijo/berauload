"""Database isolation for engineering rules."""
from sqlalchemy.orm import Session
from ...db import Metric
from .models import EngineeringRule, EngineeringRuleRevision
from .service import RULE_FIELDS
from ..org_units.references import unit_ids


def units(db: Session, include_inactive=False, unit_id=None):
    query = db.query(Metric)
    if unit_id is not None:
        query = query.filter(Metric.unit_id.in_(unit_ids(db, unit_id, active_only=not include_inactive)))
    if not include_inactive:
        query = query.filter(Metric.active.is_(True))
    return {m.code: m.unit for m in query}


def all_rules(db: Session, unit_id=None):
    return db.query(EngineeringRule).filter_by(unit_id=unit_id).order_by(EngineeringRule.id.desc()).all()


def find(db: Session, rule_id: int, unit_id=None):
    return db.query(EngineeringRule).filter_by(id=rule_id, unit_id=unit_id).first()


def find_revision(db: Session, rule_id: int, version: int):
    return db.query(EngineeringRuleRevision).filter_by(rule_id=rule_id, version=version).first()


def snapshots(db: Session, rule_id: int):
    return db.query(EngineeringRuleRevision).filter_by(rule_id=rule_id).order_by(EngineeringRuleRevision.version.desc()).all()


def add_rule(db: Session, spec: dict, user_id: int, unit_id=None):
    rule = EngineeringRule(**spec, unit_id=unit_id, created_by=user_id, version=1, status='draft')
    db.add(rule)
    db.flush()
    db.add(EngineeringRuleRevision(rule_id=rule.id, version=1,
                                  snapshot={f: spec[f].isoformat() if f == 'effective_from' else spec[f]
                                            for f in RULE_FIELDS},
                                  reason='Draft awal', created_by=user_id))
    return rule
