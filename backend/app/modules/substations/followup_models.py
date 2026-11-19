"""Stage 9d-3: follow-up (tindak lanjut) per gardu; admin-configurable types."""
from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index,
                        Integer, JSON, String, Text, UniqueConstraint)
from sqlalchemy.sql import func
from ...db import Base

STATUSES = ('terbuka', 'dikerjakan', 'selesai', 'batal')
PRIORITIES = ('rendah', 'sedang', 'tinggi')


class GarduFollowupType(Base):
    __tablename__ = 'gardu_followup_types'
    id = Column(Integer, primary_key=True)
    code = Column(String(60), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    suggest_for = Column(JSON, nullable=False, default=list)   # finding/category codes
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class GarduFollowup(Base):
    __tablename__ = 'gardu_followups'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    substation_id = Column(Integer, ForeignKey('substations.id'), nullable=False)
    measurement_id = Column(Integer, ForeignKey('substation_measurements.id'))
    type_code = Column(String(60), nullable=False)
    note = Column(Text)
    priority = Column(String(10), nullable=False, default='sedang')
    status = Column(String(12), nullable=False, default='terbuka')
    assignee = Column(String(150))
    due_on = Column(Date)
    plan = Column(JSON)   # stage 9e: snapshot of a swap/move advice at creation; NULL for ordinary tasks
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, ForeignKey('users.id'))
    updated_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("status IN ('terbuka','dikerjakan','selesai','batal')", name='ck_gardu_followup_status'),
        CheckConstraint("priority IN ('rendah','sedang','tinggi')", name='ck_gardu_followup_priority'),
        Index('ix_gardu_followup_station', 'substation_id', 'status'),
        Index('ix_gardu_followup_unit', 'unit_id', 'status'),
    )
