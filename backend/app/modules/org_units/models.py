"""New additive organizational hierarchy and mirrors; no reading data stored here."""
from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint, CheckConstraint)
from ...db import Base, now

class OrgUnit(Base):
    __tablename__ = 'org_units'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(180), nullable=False)
    level = Column(String(3), nullable=False)
    parent_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    legacy_home = Column(Boolean, nullable=False, default=False, server_default="FALSE")
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        CheckConstraint("level IN ('up3','ulp','kp')", name='ck_org_unit_level'),
        CheckConstraint("(level='up3' AND parent_id IS NULL) OR "
                        "(level IN ('ulp','kp') AND parent_id IS NOT NULL)",
                        name='ck_org_unit_parent'),
    )

class UnitDayState(Base):
    __tablename__ = 'unit_day_states'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    day = Column(Date, nullable=False)
    status = Column(String(15), nullable=False, default='draft')
    verified_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    finalized_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    note = Column(Text, nullable=True)
    __table_args__ = (UniqueConstraint('unit_id', 'day', name='uq_unit_day'),)

class UserUnitAccess(Base):
    __tablename__ = 'user_unit_access'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=False)
    role = Column(String(60), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'unit_id', name='uq_user_unit'),)
