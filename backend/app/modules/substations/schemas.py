"""Strict request models for substation master and visits."""
from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class FeederForm(Strict):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    display_order: int = 0
    active: bool = True


class FeederPatch(Strict):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    display_order: int | None = None
    active: bool | None = None


class MasterForm(Strict):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    feeder_id: int | None = None
    ownership: str | None = None
    address: str | None = None
    tap: str | None = None
    phase: Literal[1, 3] = 3
    brand: str | None = None
    power_kva: float = Field(gt=0)
    serial_number: str | None = None
    year: int | None = None
    purpose: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    line_count: int = Field(default=1, ge=1, le=5)
    line_labels: list[str] = Field(default_factory=list, max_length=5)
    extra_values: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    unit_id: int | None = None


class MasterPatch(Strict):
    code: str | None = None
    name: str | None = None
    feeder_id: int | None = None
    ownership: str | None = None
    address: str | None = None
    tap: str | None = None
    phase: Literal[1, 3] | None = None
    brand: str | None = None
    power_kva: float | None = Field(default=None, gt=0)
    serial_number: str | None = None
    year: int | None = None
    purpose: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    line_count: int | None = Field(default=None, ge=1, le=5)
    line_labels: list[str] | None = None
    extra_values: dict[str, Any] | None = None
    active: bool | None = None
    unit_id: int | None = None
    effective_on: date | None = None
    confirm_line_reduction: bool = False


class BulkMasterPatch(Strict):
    ids: list[int] = Field(min_length=1, max_length=500)
    changes: MasterPatch


class DefinitionForm(Strict):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    unit: str = Field(default='', max_length=30)
    scope: Literal['line', 'substation'] = 'line'
    min_value: float | None = None
    max_value: float | None = None
    required: bool = False
    display_order: int = 0
    active: bool = True
    kind: str | None = None
    options: list[str] | None = None


class DefinitionPatch(Strict):
    code: str | None = None
    name: str | None = None
    unit: str | None = None
    scope: Literal['line','substation'] | None = None
    min_value: float | None = None
    max_value: float | None = None
    required: bool | None = None
    display_order: int | None = None
    active: bool | None = None
    kind: str | None = None
    options: list[str] | None = None


class ValueInput(Strict):
    code: str
    line_no: int = Field(ge=0, le=5)
    value: float | str | None = None
    flag: str | None = None


class VisitForm(Strict):
    substation_id: int
    measured_on: date
    session: str
    revision: int | None = Field(default=None, ge=1)
    measured_at: str | None = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    technician: str | None = Field(default=None, max_length=150)
    note: str | None = Field(default=None, max_length=5000)
    values: list[ValueInput] = Field(default_factory=list, max_length=150)
    overwrite: bool = False


class BulkVisits(Strict):
    items: list[VisitForm] = Field(min_length=1, max_length=200)


class BulkAction(Strict):
    ids: list[int] = Field(min_length=1, max_length=500)
    action: Literal['verify', 'reopen', 'delete', 'update']
    reason: str | None = None
    changes: dict[str, Any] | None = None


class ImportApply(Strict):
    token: str
    mode: Literal['fill_empty', 'overwrite'] = 'fill_empty'
    update_existing: bool = False
    create_feeders: bool = False
