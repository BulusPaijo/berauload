"""New V1.1 tables only; existing V1 models are unchanged."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from ...db import Base, now


class FormulaDefinition(Base):
    __tablename__ = 'formula_definitions'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    metric_id = Column(Integer, ForeignKey('metrics.id'), nullable=False, unique=True)
    expression = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    # V1.1: immutable active formulas, no change to historical formula snapshots.


class SchemaMigration(Base):
    __tablename__ = 'schema_migrations'
    version = Column(String(50), primary_key=True)
    applied_at = Column(DateTime(timezone=True), default=now, nullable=False)
