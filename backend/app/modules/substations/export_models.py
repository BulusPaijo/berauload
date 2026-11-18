"""Stage 9d-2: saved gardu export templates (personal or shared, versioned)."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.sql import func
from ...db import Base


class GarduExportTemplate(Base):
    __tablename__ = 'gardu_export_templates'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(150), nullable=False)
    shared = Column(Boolean, nullable=False, default=False)
    archived = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    spec = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),
                        onupdate=func.now())
    __table_args__ = (UniqueConstraint('owner_id', 'name', 'shared', name='uq_gardu_export_tpl'),)
