"""Separate visit-based substation model; never writes HourRecord/Reading."""
from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
                        Integer, JSON, Numeric, String, Text, UniqueConstraint, Index)
from ...db import Base, now


class SubstationFeeder(Base):
    __tablename__ = 'substation_feeders'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    code = Column(String(80), nullable=False)
    name = Column(String(180), nullable=False)
    description = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    __table_args__ = (UniqueConstraint('unit_id', 'code', name='uq_substation_feeder_code'),)


class SubstationChoice(Base):
    __tablename__ = 'substation_choices'
    id = Column(Integer, primary_key=True)
    kind = Column(String(20), nullable=False)
    code = Column(String(80), nullable=False)
    name = Column(String(180), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint('kind', 'code', name='uq_substation_choice'),
                      CheckConstraint("kind IN ('ownership','purpose')", name='ck_substation_choice_kind'))


class Substation(Base):
    __tablename__ = 'substations'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    code = Column(String(80), nullable=False)
    name = Column(String(180), nullable=False)
    feeder_id = Column(Integer, ForeignKey('substation_feeders.id'))
    ownership = Column(String(80))
    address = Column(Text)
    tap = Column(String(60))
    phase = Column(Integer, nullable=False, default=3)
    brand = Column(String(120))
    power_kva = Column(Numeric(12, 3), nullable=False)
    serial_number = Column(String(120))
    year = Column(Integer)
    purpose = Column(String(80))
    lat = Column(Numeric(11, 7))
    lon = Column(Numeric(11, 7))
    line_count = Column(Integer, nullable=False, default=1)
    line_labels = Column(JSON, nullable=False, default=list)
    extra_values = Column(JSON, nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    updated_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint('unit_id', 'code', name='uq_substation_unit_code'),
        CheckConstraint('line_count BETWEEN 1 AND 5', name='ck_substation_line_count'),
        CheckConstraint('phase IN (1,3)', name='ck_substation_phase'),
        CheckConstraint('power_kva > 0', name='ck_substation_power'),
        Index('ix_substation_unit_feeder', 'unit_id', 'feeder_id', 'active'),
    )


class SubstationMasterHistory(Base):
    __tablename__ = 'substation_master_history'
    id = Column(Integer, primary_key=True)
    substation_id = Column(Integer, ForeignKey('substations.id'), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=now)
    effective_on = Column(Date, nullable=False)
    changed_by = Column(Integer, ForeignKey('users.id'))
    changes = Column(JSON, nullable=False)


class SubstationParam(Base):
    __tablename__ = 'substation_params'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(180), nullable=False)
    unit = Column(String(30), nullable=False)
    scope = Column(String(15), nullable=False)
    value_type = Column(String(15), nullable=False, default='number')
    min_value = Column(Numeric(18, 6))
    max_value = Column(Numeric(18, 6))
    display_order = Column(Integer, nullable=False, default=0)
    required = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("scope IN ('line','substation')", name='ck_substation_param_scope'),)


class SubstationSession(Base):
    __tablename__ = 'substation_sessions'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class SubstationValueFlag(Base):
    __tablename__ = 'substation_value_flags'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class SubstationField(Base):
    __tablename__ = 'substation_fields'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    kind = Column(String(15), nullable=False)
    options = Column(JSON, nullable=False, default=list)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("kind IN ('text','number','choice')", name='ck_substation_field_kind'),)


class SubstationMeasurement(Base):
    __tablename__ = 'substation_measurements'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    substation_id = Column(Integer, ForeignKey('substations.id'), nullable=False)
    measured_on = Column(Date, nullable=False)
    session = Column(String(80), nullable=False)
    measured_at = Column(String(5))
    technician = Column(String(150))
    note = Column(Text)
    state = Column(String(12), nullable=False, default='draft')
    revision = Column(Integer, nullable=False, default=1)
    snapshot_power_kva = Column(Numeric(12, 3), nullable=False)
    snapshot_phase = Column(Integer, nullable=False)
    snapshot_line_count = Column(Integer, nullable=False)
    snapshot_feeder_id = Column(Integer, ForeignKey('substation_feeders.id'))
    created_by = Column(Integer, ForeignKey('users.id'))
    updated_by = Column(Integer, ForeignKey('users.id'))
    verified_by = Column(Integer, ForeignKey('users.id'))
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    __table_args__ = (
        UniqueConstraint('substation_id', 'measured_on', 'session', name='uq_substation_visit'),
        CheckConstraint("state IN ('draft','verified')", name='ck_substation_measurement_state'),
        Index('ix_substation_visit_unit_date', 'unit_id', 'measured_on', 'session'),
    )


class SubstationValue(Base):
    __tablename__ = 'substation_values'
    id = Column(Integer, primary_key=True)
    measurement_id = Column(Integer, ForeignKey('substation_measurements.id'), nullable=False)
    param_id = Column(Integer, ForeignKey('substation_params.id'), nullable=False)
    line_no = Column(Integer, nullable=False)
    value = Column(Numeric(18, 6))
    flag = Column(String(80))
    __table_args__ = (
        UniqueConstraint('measurement_id', 'param_id', 'line_no', name='uq_substation_value'),
        CheckConstraint('line_no BETWEEN 0 AND 5', name='ck_substation_value_line'),
        CheckConstraint('value IS NULL OR flag IS NULL', name='ck_substation_value_flag'),
    )
