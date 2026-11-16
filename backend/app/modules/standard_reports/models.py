"""Scoped report comparison preferences. No measurement data is persisted here."""
from sqlalchemy import ForeignKey
from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from ...db import Base, now


class StandardReportSelection(Base):
    __tablename__ = 'standard_report_selections'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    scope = Column(String(12), nullable=False)
    owner_id = Column(Integer, nullable=False, default=0)
    metric_code = Column(String(90), nullable=False)
    aggregation = Column(String(8), nullable=False, default='max')
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint('scope', 'owner_id', name='uq_std_report_selection'),)
