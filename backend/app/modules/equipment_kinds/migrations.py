"""Additive, re-runnable equipment kind migration. Never rewrites Asset.kind."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import EquipmentKind

VERSION = '20261114_02_equipment_kinds'
DEFAULT_KINDS = (
    ('pembangkit', 'Pembangkit'), ('feeder', 'Feeder / Penyulang'),
    ('incoming', 'Incoming'), ('sistem', 'Sistem'), ('lain', 'Peralatan lainnya'),
)


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        EquipmentKind.__table__.create(conn, checkfirst=True)
        # Seeding on each run also backfills codes that predate this release.
        from ...db import Asset
        existing = set(conn.execute(select(EquipmentKind.code)).scalars())
        for order, (code, name) in enumerate(DEFAULT_KINDS):
            if code not in existing:
                conn.execute(EquipmentKind.__table__.insert().values(
                    code=code, name=name, active=True, display_order=order))
                existing.add(code)
        for code in conn.execute(select(Asset.kind).distinct()).scalars():
            if code not in existing:
                conn.execute(EquipmentKind.__table__.insert().values(
                    code=code, name=code.replace('_', ' ').title(),
                    active=True, display_order=100))
                existing.add(code)
        if not conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).first():
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
