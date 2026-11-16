"""Stored export column layouts, no measurements are copied here."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from ...db import Base, now


class ExportTemplate(Base):
    __tablename__ = 'export_templates'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    name = Column(String(150), nullable=False)
    scope = Column(String(10), nullable=False, default='personal')
    owner_id = Column(Integer, nullable=False)
    spec = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
