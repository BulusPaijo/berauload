"""Current historical definitions and immutable, user-auditable revision snapshots."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from ...db import Base, now


class HistoricalDefinition(Base):
    __tablename__ = 'historical_definitions'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    code = Column(String(90), unique=True, nullable=False)
    name = Column(String(180), nullable=False)
    expression = Column(Text, nullable=False)
    unit = Column(String(12), nullable=False)
    aggregation = Column(String(12), nullable=False)
    resolution = Column(String(12), nullable=False)
    mode = Column(String(16), nullable=False)
    moving_days = Column(Integer, nullable=False, default=7)
    hour_start = Column(Integer, nullable=False, default=0)
    hour_end = Column(Integer, nullable=False, default=23)
    version = Column(Integer, nullable=False, default=1)
    archived = Column(Boolean, nullable=False, default=False)
    created_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class HistoricalRevision(Base):
    __tablename__ = 'historical_revisions'
    id = Column(Integer, primary_key=True)
    definition_id = Column(Integer, ForeignKey('historical_definitions.id'), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    reason = Column(String(500), nullable=False)
    created_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('definition_id', 'version', name='uq_historical_revision'),)
