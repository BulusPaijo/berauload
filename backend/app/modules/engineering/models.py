"""Engineering rules are advisory; no control-system output or automatic alerts."""
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from ...db import Base, now


class EngineeringRule(Base):
    __tablename__ = 'engineering_rules'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    code = Column(String(90), unique=True, nullable=False)
    name = Column(String(180), nullable=False)
    expression = Column(Text, nullable=False)
    unit = Column(String(12), nullable=False)
    direction = Column(String(8), nullable=False)  # below / above
    warning_threshold = Column(Float, nullable=False)
    critical_threshold = Column(Float, nullable=False)
    reference_note = Column(String(500), nullable=False)
    effective_from = Column(Date, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(12), nullable=False, default='draft')  # draft, active, archived
    created_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class EngineeringRuleRevision(Base):
    __tablename__ = 'engineering_rule_revisions'
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('engineering_rules.id'), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    reason = Column(String(500), nullable=False)
    created_by = Column(ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint('rule_id', 'version', name='uq_engineering_rule_revision'),)
