"""Idempotent, additive V1.1 migration. No ALTER/DROP of V1 data tables."""
from sqlalchemy import select
from .models import FormulaDefinition, SchemaMigration

VERSION = '20261113_01_formula_builder_core'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        old = conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).scalar_one_or_none()
        if old is None:
            FormulaDefinition.__table__.create(conn, checkfirst=True)
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
