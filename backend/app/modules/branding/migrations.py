"""Additive, restart-safe branding store for PostgreSQL and SQLite."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import AppBranding

VERSION = '20261117_16_stage8_branding'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        AppBranding.__table__.create(conn, checkfirst=True)
        if conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first() is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
