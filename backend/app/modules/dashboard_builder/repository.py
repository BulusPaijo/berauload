"""All persistence for dashboard layout feature."""
from sqlalchemy.orm import Session
from .models import DashboardLayout, DashboardShare, DashboardRevision
from sqlalchemy import select


def visible(db: Session, user_id: int, unit_id: int, include_archived: bool = False):
    q = db.query(DashboardLayout).filter(DashboardLayout.unit_id==unit_id,
        (DashboardLayout.scope == 'system') |
        ((DashboardLayout.scope == 'personal') & (DashboardLayout.owner_id == user_id)) |
        (DashboardLayout.id.in_(select(DashboardShare.layout_id).where(DashboardShare.user_id == user_id))))
    if not include_archived:
        q = q.filter(DashboardLayout.archived.is_(False))
    return q.order_by(DashboardLayout.scope, DashboardLayout.name, DashboardLayout.id).all()


def clear_default(db: Session, scope: str, owner_id: int, unit_id: int):
    db.query(DashboardLayout).filter_by(scope=scope, owner_id=owner_id, is_default=True, unit_id=unit_id).update(
        {'is_default': False}, synchronize_session=False)


def count_active(db: Session, scope: str, owner_id: int, unit_id: int) -> int:
    return db.query(DashboardLayout).filter_by(
        scope=scope, owner_id=owner_id, archived=False, unit_id=unit_id).count()


def snapshot(item: DashboardLayout) -> dict:
    return {'name': item.name, 'description': item.description,
            'panels': [dict(p) for p in item.panels]}


def record_revision(db: Session, item: DashboardLayout, actor: int | None):
    db.add(DashboardRevision(layout_id=item.id, version=item.version,
                             snapshot=snapshot(item), updated_by=actor))
