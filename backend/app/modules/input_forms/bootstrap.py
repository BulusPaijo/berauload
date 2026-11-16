"""Seed default tabs for a newly created unit, not on startup/restart."""
from .migrations import DEFAULT_TABS
from .models import InputFormTab, InputFormRevision


def seed_unit_tabs(db, unit):
    if unit.level == 'up3':
        return
    for order, (code, name) in enumerate(DEFAULT_TABS):
        db.add(InputFormTab(unit_id=unit.id, code=f'u{unit.id}_{code}',
                            name=name, display_order=order, active=True))
    db.add(InputFormRevision(unit_id=unit.id, version=1))
