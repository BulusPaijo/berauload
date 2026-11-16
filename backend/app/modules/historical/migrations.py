"""V1.2.1 additive schema update, snapshots old definitions without changing calculations."""
from sqlalchemy import inspect, select, text
from ..formulas.models import SchemaMigration
from .models import HistoricalDefinition, HistoricalRevision

VERSION = '20261114_04_historical_revision_management'
FIELDS = ('code', 'name', 'expression', 'unit', 'aggregation', 'resolution',
          'mode', 'moving_days', 'hour_start', 'hour_end')


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        HistoricalDefinition.__table__.create(conn, checkfirst=True)
        columns = {c['name'] for c in inspect(conn).get_columns('historical_definitions')}
        if 'unit_id' not in columns:
            conn.execute(text('ALTER TABLE historical_definitions ADD COLUMN unit_id INTEGER REFERENCES org_units(id)'))
        if 'archived' not in columns:
            conn.execute(text('ALTER TABLE historical_definitions ADD COLUMN archived BOOLEAN NOT NULL DEFAULT FALSE'))
        HistoricalRevision.__table__.create(conn, checkfirst=True)
        for existing in conn.execute(select(HistoricalDefinition.__table__)).mappings():
            identity = existing['id']
            version = existing['version']
            found = conn.execute(select(HistoricalRevision.id).where(
                HistoricalRevision.definition_id == identity,
                HistoricalRevision.version == version)).first()
            if found is None:
                snapshot = {field: existing[field] for field in FIELDS}
                conn.execute(HistoricalRevision.__table__.insert().values(
                    definition_id=identity, version=version, snapshot=snapshot,
                    reason='Snapshot migrasi definisi V1.2.0', created_by=existing['created_by']))
        known = conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first()
        if known is None:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
