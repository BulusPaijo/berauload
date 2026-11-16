"""One-time additive metadata migration. Historical import endpoint is unchanged."""
from sqlalchemy import inspect, select, text
from ..formulas.models import SchemaMigration

VERSION = '20261115_13_template_import_batch_kind'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        columns = {c['name'] for c in inspect(conn).get_columns('import_batches')}
        if 'kind' not in columns:
            conn.execute(text("ALTER TABLE import_batches ADD COLUMN kind VARCHAR(20) DEFAULT 'legacy_excel'"))
        pending = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).scalar_one_or_none() is None
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_template_file_per_unit "
                          "ON import_batches (unit_id, sha256) WHERE kind='template'"))
        if pending:
            conn.execute(text("UPDATE import_batches SET kind='legacy_excel' WHERE kind IS NULL"))
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
