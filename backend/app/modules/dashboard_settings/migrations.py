"""Idempotent additive migration; existing reading/formula tables untouched."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import DashboardChartSettings

VERSION = '20261113_02_dashboard_chart_settings'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        DashboardChartSettings.__table__.create(conn, checkfirst=True)
        exists = conn.execute(
            select(SchemaMigration.version).where(SchemaMigration.version == VERSION)
        ).scalar_one_or_none()
        if exists is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
