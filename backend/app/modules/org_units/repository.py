"""Database operations for organization configuration (no reading filters)."""
from sqlalchemy import select
from ...db import Metric, now
from .models import OrgUnit, UserUnitAccess, UnitDayState

def root(db):
    """The one root is identified by its immutable level, not by a name/code."""
    return db.query(OrgUnit).filter_by(level='up3').one()

def home_unit(db):
    """Default owner for legacy measurements; never the UP3 root."""
    return db.query(OrgUnit).filter_by(legacy_home=True).one()

def units(db):
    return db.query(OrgUnit).order_by(OrgUnit.display_order, OrgUnit.id).all()

def unit_dict(row):
    return {key: getattr(row, key) for key in
            ('id', 'code', 'name', 'level', 'parent_id', 'active', 'display_order', 'legacy_home')}

def access_rows(db, unit_id):
    return db.query(UserUnitAccess).filter_by(unit_id=unit_id).order_by(UserUnitAccess.user_id).all()

def role_conflict(db, unit_id, role_key, except_id=None):
    query = db.query(Metric.id).filter_by(unit_id=unit_id, role_key=role_key)
    if except_id is not None:
        query = query.filter(Metric.id != except_id)
    return query.first() is not None

def attach_new_user(db, user):
    """Called for new legacy users without changing global role enforcement."""
    db.flush()
    target = root(db) if user.role in ('admin','management') else home_unit(db)
    db.add(UserUnitAccess(user_id=user.id, unit_id=target.id, role=user.role))


def mirror_day_state(db, state):
    """Same-transaction home-unit mirror; day_states remains read source."""
    unit_id = home_unit(db).id
    row = db.query(UnitDayState).filter_by(unit_id=unit_id, day=state.day).first()
    if row is None:
        row = UnitDayState(unit_id=unit_id, day=state.day)
        db.add(row)
    row.status, row.verified_by, row.finalized_by = (
        state.status, state.verified_by, state.finalized_by)
    row.note, row.updated_at = state.note, now()
