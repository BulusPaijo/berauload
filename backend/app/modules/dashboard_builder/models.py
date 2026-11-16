"""Dashboard layout settings. Never stores readings or electrical calculations."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from ...db import Base, now


class DashboardLayout(Base):
    __tablename__ = 'dashboard_layouts'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(String(500), nullable=False, default='')
    scope = Column(String(10), nullable=False)  # system / personal
    owner_id = Column(Integer, nullable=False, default=0)
    panels = Column(JSON, nullable=False, default=list)
    version = Column(Integer, nullable=False, default=1)
    is_default = Column(Boolean, nullable=False, default=False)
    archived = Column(Boolean, nullable=False, default=False)
    updated_by = Column(ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)


class DashboardRevision(Base):
    """Immutable dashboard layout snapshots for rollback and audit."""
    __tablename__ = 'dashboard_revisions'
    id = Column(Integer, primary_key=True)
    layout_id = Column(ForeignKey('dashboard_layouts.id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    updated_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (UniqueConstraint('layout_id', 'version', name='uq_dashboard_revision'),)


class DashboardShare(Base):
    """Read-only sharing of a personal dashboard with an explicit user."""
    __tablename__ = 'dashboard_shares'
    id = Column(Integer, primary_key=True)
    layout_id = Column(ForeignKey('dashboard_layouts.id'), nullable=False, index=True)
    user_id = Column(ForeignKey('users.id'), nullable=False, index=True)
    __table_args__ = (UniqueConstraint('layout_id', 'user_id', name='uq_dashboard_share'),)
