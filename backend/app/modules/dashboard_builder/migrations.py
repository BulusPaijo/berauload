"""Small additive/idempotent V1.4 schema migration, no change to existing readings."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import DashboardLayout, DashboardRevision, DashboardShare

VERSION = '20261114_01_dashboard_builder'
DEFAULT_PANELS = [
    {'id': 'default-hj', 'title': 'Daya Mampu vs Beban Sistem', 'kind': 'line',
     'source': 'metric', 'metric_codes': ['daya_pasok_pembangkit_kw', 'beban_sistem_kw'],
     'aggregation': 'avg', 'w': 12, 'h': 2},
    {'id': 'default-peak', 'title': 'Beban Puncak', 'kind': 'stat',
     'source': 'metric', 'metric_codes': ['beban_sistem_kw'],
     'aggregation': 'peak', 'w': 4, 'h': 1},
    {'id': 'default-capacity', 'title': 'Rata-rata Daya Mampu', 'kind': 'stat',
     'source': 'metric', 'metric_codes': ['daya_pasok_pembangkit_kw'],
     'aggregation': 'avg', 'w': 4, 'h': 1},
    {'id': 'default-min', 'title': 'Beban Minimum', 'kind': 'stat',
     'source': 'metric', 'metric_codes': ['beban_sistem_kw'],
     'aggregation': 'min', 'w': 4, 'h': 1},
]


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        DashboardLayout.__table__.create(conn, checkfirst=True)
        recorded = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).scalar_one_or_none()
        if recorded is None:
            existing = conn.execute(select(DashboardLayout.id).where(
                DashboardLayout.scope == 'system')).first()
            if existing is None:
                conn.execute(DashboardLayout.__table__.insert().values(
                    name='Monitoring Operasi Berau',
                    description='Dashboard resmi awal: daya mampu kolom H dan beban sistem kolom J.',
                    scope='system', owner_id=0, panels=DEFAULT_PANELS,
                    is_default=True, archived=False, version=1))
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))


MANAGEMENT_VERSION = '20261114_05_dashboard_management'


def run_management(engine):
    """Backfill the current layout as the first known snapshot; no fabricated older versions."""
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        DashboardLayout.__table__.create(conn, checkfirst=True)
        DashboardRevision.__table__.create(conn, checkfirst=True)
        DashboardShare.__table__.create(conn, checkfirst=True)
        existing = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == MANAGEMENT_VERSION)).scalar_one_or_none()
        if existing is not None:
            return
        for item in conn.execute(select(DashboardLayout)).mappings():
            exists = conn.execute(select(DashboardRevision.id).where(
                DashboardRevision.layout_id == item['id'],
                DashboardRevision.version == item['version'])).first()
            if exists is None:
                conn.execute(DashboardRevision.__table__.insert().values(
                    layout_id=item['id'], version=item['version'],
                    snapshot={'name': item['name'], 'description': item['description'],
                              'panels': item['panels'] or []}, updated_by=item['updated_by']))
        conn.execute(SchemaMigration.__table__.insert().values(version=MANAGEMENT_VERSION))
