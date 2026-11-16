"""Idempotent additive migration, without touching existing reading or formula tables."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import StandardReportSelection

VERSION = '20261114_01_standard_report_selection'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        StandardReportSelection.__table__.create(conn, checkfirst=True)
        found = conn.execute(
            select(SchemaMigration.version).where(SchemaMigration.version == VERSION)
        ).scalar_one_or_none()
        if found is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
