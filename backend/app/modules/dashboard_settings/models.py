"""Additive persistence for dashboard chart defaults and user preferences."""
from sqlalchemy import ForeignKey
from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint
from ...db import Base, now


class DashboardChartSettings(Base):
    __tablename__ = 'dashboard_chart_settings'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    scope = Column(String(12), nullable=False)  # 'system' or 'user'
    owner_id = Column(Integer, nullable=False, default=0)  # system=0; user=user.id
    metric_codes = Column(JSON, nullable=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint('scope', 'owner_id', name='uq_chart_scope_owner'),)
