"""Database operations for chart configuration, isolated from controllers."""
from sqlalchemy.orm import Session
from .models import DashboardChartSettings


def get_settings(db: Session, scope: str, owner_id: int, unit_id: int):
    from ..org_units.scoping import scoped_owner
    row = db.query(DashboardChartSettings).filter_by(
        scope=scoped_owner(db, scope, unit_id), owner_id=owner_id, unit_id=unit_id).first()
    if row is None and scope == 'user':
        row = db.query(DashboardChartSettings).filter_by(
            scope='user', owner_id=owner_id, unit_id=unit_id).first()
    return row


def save_settings(db: Session, scope: str, owner_id: int, codes: list[str], user_id: int, unit_id: int):
    from ..org_units.scoping import scoped_owner
    entry = get_settings(db, scope, owner_id, unit_id)
    if entry is None:
        entry = DashboardChartSettings(scope=scoped_owner(db, scope, unit_id), unit_id=unit_id,
                                       owner_id=owner_id, metric_codes=codes)
        db.add(entry)
    entry.metric_codes = list(codes)
    entry.updated_by = user_id
    return entry


def delete_personal(db: Session, user_id: int, unit_id: int):
    entry = get_settings(db, 'user', user_id, unit_id)
    if entry:
        db.delete(entry)
    return entry is not None
