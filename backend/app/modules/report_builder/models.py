"""Persistent report layouts. Reports only reference measurements; no data is copied."""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey
from ...db import Base, now


class ReportTemplate(Base):
    __tablename__ = 'report_templates'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(String(500), default='', nullable=False)
    scope = Column(String(12), nullable=False, default='personal')
    owner_id = Column(Integer, nullable=False)
    blocks = Column(JSON, nullable=False, default=list)
    version = Column(Integer, nullable=False, default=1)
    archived = Column(Boolean, nullable=False, default=False)
    updated_by = Column(ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
