"""Presentation configuration. Metric codes and original group_name never change."""
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean, Column, Integer, String
from ...db import Base


class InputFormTab(Base):
    __tablename__ = 'input_form_tabs'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    code = Column(String(40), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class InputFormPlacement(Base):
    __tablename__ = 'input_form_placements'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    metric_code = Column(String(90), nullable=False, unique=True, index=True)
    tab_code = Column(String(40), nullable=False, index=True)
    display_order = Column(Integer, nullable=False, default=0)
    visible = Column(Boolean, nullable=False, default=True)


class InputFormRevision(Base):
    __tablename__ = 'input_form_revision'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    version = Column(Integer, nullable=False, default=1)
