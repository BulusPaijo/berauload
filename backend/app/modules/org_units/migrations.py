"""Additive, idempotent PostgreSQL/SQLite migration; do not modify readings."""
from sqlalchemy import inspect, select, text
from ..formulas.models import SchemaMigration
from .models import OrgUnit, UnitDayState, UserUnitAccess

VERSION = '20261115_11_org_units_stage1'


def precreate(engine):
    """Create org_units before fresh legacy tables that reference its FK."""
    with engine.begin() as conn:
        OrgUnit.__table__.create(conn, checkfirst=True)


def _add_columns(conn):
    spec = {'assets': [('unit_id', 'INTEGER REFERENCES org_units(id)')],
            'metrics': [('unit_id', 'INTEGER REFERENCES org_units(id)'),
                        ('role_key', 'VARCHAR(60)')],
            'import_batches': [('unit_id', 'INTEGER REFERENCES org_units(id)')]}
    for table, fields in spec.items():
        existing = {c['name'] for c in inspect(conn).get_columns(table)}
        for name, definition in fields:
            if name not in existing:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))


def _seed_and_backfill(conn):
    table = OrgUnit.__table__
    first = conn.execute(select(table.c.id, table.c.code).limit(1)).first()
    if first is None:
        conn.execute(table.insert().values(code='up3_berau', name='UP3 Berau',
                                            level='up3', parent_id=None,
                                            active=True, display_order=0))
    root_id = conn.execute(select(table.c.id).where(table.c.code == 'up3_berau')).scalar_one_or_none()
    if root_id is None:
        raise RuntimeError('Hierarki tidak mempunyai UP3 Berau; migrasi dihentikan')
    for table_name in ('assets', 'metrics', 'import_batches'):
        conn.execute(text(f'UPDATE {table_name} SET unit_id=:id WHERE unit_id IS NULL'), {'id': root_id})
    mapping = {'beban_sistem_kw': 'system.load',
               'daya_pasok_pembangkit_kw': 'system.capacity'}
    for code, key in mapping.items():
        conn.execute(text('UPDATE metrics SET role_key=:key WHERE code=:code AND role_key IS NULL'),
                     {'key': key, 'code': code})
    return root_id


def _copy_states_and_users(conn, root_id, owner_id):
    """Stage 1 fallback: older database stays on root until Stage 1.1 rehomes."""
    conn.execute(text("""INSERT INTO unit_day_states
        (unit_id, day, status, verified_by, finalized_by, updated_at, note)
        SELECT :owner, d.day, d.status, d.verified_by, d.finalized_by,
               COALESCE(d.updated_at,CURRENT_TIMESTAMP), d.note
        FROM day_states d WHERE NOT EXISTS
        (SELECT 1 FROM unit_day_states u WHERE u.unit_id=:owner AND u.day=d.day)"""),
        {'owner': owner_id})
    conn.execute(text("""INSERT INTO user_unit_access (user_id, unit_id, role)
        SELECT u.id, CASE WHEN u.role='admin' THEN :root ELSE :owner END, u.role
        FROM users u WHERE NOT EXISTS
        (SELECT 1 FROM user_unit_access a WHERE a.user_id=u.id AND
          a.unit_id=CASE WHEN u.role='admin' THEN :root ELSE :owner END)"""),
        {'root': root_id, 'owner': owner_id})


def _home_id(conn, root_id):
    if 'legacy_home' not in {c['name'] for c in inspect(conn).get_columns('org_units')}:
        return root_id
    return conn.execute(text("SELECT id FROM org_units WHERE legacy_home=TRUE")).scalar_one_or_none() or root_id


def run(engine):
    precreate(engine)
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        UnitDayState.__table__.create(conn, checkfirst=True)
        UserUnitAccess.__table__.create(conn, checkfirst=True)
        _add_columns(conn)
        pending = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).scalar_one_or_none() is None
        if pending:
            root_id = _seed_and_backfill(conn)
        else:
            root_id = conn.execute(select(OrgUnit.id).where(
                OrgUnit.level == 'up3')).scalar_one()
            # Repair rows created by legacy source during a code-only rollback.
            for table_name in ('assets', 'metrics', 'import_batches'):
                conn.execute(text(f'UPDATE {table_name} SET unit_id=:id WHERE unit_id IS NULL'),
                             {'id': _home_id(conn, root_id)})
        if pending:
            _copy_states_and_users(conn, root_id, _home_id(conn, root_id))
        conn.execute(text("""CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_unit_role_key
                             ON metrics (unit_id, role_key)"""))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_org_single_up3 "
                          "ON org_units (level) WHERE level='up3'"))
        if pending:
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
