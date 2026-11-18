"""Versioned global gardu calculations, separated from immutable measurement input."""
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index,
                        Integer, JSON, String, Text, UniqueConstraint)
from ...db import Base, now


class GarduCalcColumn(Base):
    __tablename__ = 'gardu_calc_columns'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=False, unique=True)
    name = Column(String(180), nullable=False)
    unit = Column(String(30), nullable=False, default='—')
    decimals = Column(Integer, nullable=False, default=1)
    expression = Column(String(500), nullable=False)
    empty_mode = Column(String(12), nullable=False, default='batal')
    description = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    origin = Column(String(12), nullable=False, default='custom')
    default_expression = Column(String(500))
    default_snapshot = Column(JSON)


class GarduCalcRule(Base):
    __tablename__ = 'gardu_calc_rules'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=False, unique=True)
    name = Column(String(180), nullable=False)
    kind = Column(String(16), nullable=False)  # category | finding
    group_name = Column(String(100), nullable=False, default='Pembebanan')
    expression = Column(String(500), nullable=False)
    color = Column(String(7), nullable=False, default='#607d8b')
    marker = Column(String(15), nullable=False, default='circle')
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    origin = Column(String(12), nullable=False, default='custom')


class GarduCalcConstant(Base):
    __tablename__ = 'gardu_calc_constants'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=False, unique=True)
    name = Column(String(180), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False, default='—')
    description = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class GarduCalcHistory(Base):
    __tablename__ = 'gardu_calc_history'
    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False)
    code = Column(String(80), nullable=False)
    version = Column(Integer, nullable=False)
    changed_by = Column(Integer, ForeignKey('users.id'))
    changed_at = Column(DateTime(timezone=True), nullable=False, default=now)
    before = Column(JSON)
    after = Column(JSON)
    __table_args__ = (Index('ix_gardu_calc_history_kind_code', 'kind', 'code'),)


class GarduCalcSettings(Base):
    __tablename__ = 'gardu_calc_settings'
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    stale_days = Column(Integer, nullable=False, default=180)
    pending = Column(Boolean, nullable=False, default=True)


class GarduCalcValue(Base):
    __tablename__ = 'gardu_calc_values'
    id = Column(Integer, primary_key=True)
    measurement_id = Column(Integer, ForeignKey('substation_measurements.id'), nullable=False)
    column_id = Column(Integer, ForeignKey('gardu_calc_columns.id'), nullable=False)
    value = Column(Float)
    incomplete = Column(Boolean, nullable=False, default=False)
    filled = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    note = Column(Text)
    version = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('measurement_id', 'column_id', name='uq_gardu_calc_value'),
                      Index('ix_gardu_calc_value_sort', 'column_id', 'value'))


class GarduCalcMatch(Base):
    __tablename__ = 'gardu_calc_matches'
    id = Column(Integer, primary_key=True)
    measurement_id = Column(Integer, ForeignKey('substation_measurements.id'), nullable=False)
    rule_id = Column(Integer, ForeignKey('gardu_calc_rules.id'), nullable=False)
    version = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('measurement_id', 'rule_id', name='uq_gardu_calc_match'),
                      Index('ix_gardu_calc_match_rule', 'rule_id', 'measurement_id'))


class GarduCalcMark(Base):
    __tablename__ = 'gardu_calc_marks'
    measurement_id = Column(Integer, ForeignKey('substation_measurements.id'), primary_key=True)
    version = Column(Integer, nullable=False)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=now)
