"""Resolve semantic metric roles without hard-coded codes or cross-unit fallback."""
from sqlalchemy.orm import Session
from ...db import Metric

SYSTEM_LOAD = 'system.load'
SYSTEM_CAPACITY = 'system.capacity'
MAIN_ROLES = (SYSTEM_LOAD, SYSTEM_CAPACITY)


def metric_for_role(db: Session, unit_id: int, role_key: str) -> Metric | None:
    """An inactive or missing role is unconfigured, never a guessed metric."""
    return (db.query(Metric).filter_by(unit_id=unit_id, role_key=role_key,
                                      active=True).first())


def role_codes(db: Session, unit_id: int) -> dict[str, str]:
    """Active mappings for exactly one unit; generic roles may also appear."""
    return {m.role_key: m.code for m in db.query(Metric).filter_by(
        unit_id=unit_id, active=True).all() if m.role_key}


def main_pair(db: Session, unit_id: int) -> tuple[Metric | None, Metric | None]:
    return (metric_for_role(db, unit_id, SYSTEM_CAPACITY),
            metric_for_role(db, unit_id, SYSTEM_LOAD))


def required_role(db: Session, unit_id: int, role_key: str) -> Metric | None:
    """Explicit alias for callers that need a nullable source, not an exception."""
    return metric_for_role(db, unit_id, role_key)
