"""V1.6.0 Stage 1.1: transactional rehome of legacy ownership, not readings.

Runs after the Stage 1 migration. Handles both Stage 1 and Stage 4.2 upgrades.
"""
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from ...db import AuditLog
from ..formulas.models import SchemaMigration

VERSION = '20261115_12_legacy_home_ulp_tanjung_redeb'
HOME_CODE = 'ulp_tanjung_redeb'


def _ensure_column_and_index(conn):
    columns = {c['name'] for c in inspect(conn).get_columns('org_units')}
    if 'legacy_home' not in columns:
        conn.execute(text('ALTER TABLE org_units ADD COLUMN legacy_home BOOLEAN NOT NULL DEFAULT FALSE'))
    conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_org_single_legacy_home '
                      'ON org_units (legacy_home) WHERE legacy_home=TRUE'))


def _seed_home(conn):
    roots = conn.execute(text("SELECT id FROM org_units WHERE level='up3'")).scalars().all()
    if len(roots) != 1:
        raise RuntimeError('Migrasi legacy_home: jumlah UP3 harus tepat satu')
    root_id = roots[0]
    home = conn.execute(text('SELECT id,level,parent_id,active,legacy_home '
                             'FROM org_units WHERE code=:code'), {'code': HOME_CODE}).mappings().first()
    if home is None:
        conn.execute(text('INSERT INTO org_units '
            '(code,name,level,parent_id,active,legacy_home,display_order,created_at) '
            "VALUES (:code,'ULP Tanjung Redeb','ulp',:root,TRUE,TRUE,0,CURRENT_TIMESTAMP)"),
            {'code': HOME_CODE, 'root': root_id})
    elif home['level'] != 'ulp' or home['parent_id'] != root_id or not home['active']:
        raise RuntimeError('Unit ulp_tanjung_redeb telah ada dengan hierarki/status yang tidak sesuai')
    home_id = conn.execute(text('SELECT id FROM org_units WHERE code=:code'),
                           {'code': HOME_CODE}).scalar_one()
    others = conn.execute(text('SELECT id FROM org_units WHERE legacy_home=TRUE AND id<>:home'),
                          {'home': home_id}).all()
    if others:
        raise RuntimeError('Sudah ada unit legacy_home lain; migrasi dibatalkan')
    conn.execute(text('UPDATE org_units SET legacy_home=TRUE WHERE id=:home'), {'home': home_id})
    return root_id, home_id


def _rehome_tables(conn, root_id, home_id):
    counts = {}
    for table in ('assets', 'metrics', 'import_batches'):
        result = conn.execute(text(f'UPDATE {table} SET unit_id=:home '
                                   'WHERE unit_id=:root OR unit_id IS NULL'),
                              {'home': home_id, 'root': root_id})
        counts[table] = result.rowcount
    return counts


def _move_day_states(conn, root_id, home_id):
    mirrors = conn.execute(text('SELECT id,day,status,verified_by,finalized_by,note '
                                'FROM unit_day_states WHERE unit_id=:root'),
                           {'root': root_id}).mappings().all()
    moved = 0
    for row in mirrors:
        target = conn.execute(text('SELECT id,status,verified_by,finalized_by,note '
                                   'FROM unit_day_states WHERE unit_id=:home AND day=:day'),
                              {'home': home_id, 'day': row['day']}).mappings().first()
        if target:
            columns = ('status', 'verified_by', 'finalized_by', 'note')
            if any(target[col] != row[col] for col in columns):
                raise RuntimeError(f'Konflik status hari {row["day"]}; migrasi dihentikan')
            conn.execute(text('DELETE FROM unit_day_states WHERE id=:id'), {'id': row['id']})
        else:
            conn.execute(text('UPDATE unit_day_states SET unit_id=:home WHERE id=:id'),
                         {'home': home_id, 'id': row['id']})
        moved += 1
    return moved


def _move_nonadmin_access(conn, root_id, home_id):
    legacy = conn.execute(text('SELECT a.id,a.user_id,a.role FROM user_unit_access a '
             "JOIN users u ON u.id=a.user_id WHERE a.unit_id=:root AND u.role<>'admin'"),
             {'root': root_id}).mappings().all()
    for row in legacy:
        existing = conn.execute(text('SELECT role FROM user_unit_access '
                        'WHERE unit_id=:home AND user_id=:user'),
                        {'home': home_id, 'user': row['user_id']}).scalar_one_or_none()
        if existing is not None:
            if existing != row['role']:
                raise RuntimeError(f'Konflik akses pengguna {row["user_id"]}; migrasi dihentikan')
            conn.execute(text('DELETE FROM user_unit_access WHERE id=:id'), {'id': row['id']})
        else:
            conn.execute(text('UPDATE user_unit_access SET unit_id=:home WHERE id=:id'),
                         {'home': home_id, 'id': row['id']})
    return len(legacy)


def _assert_root_empty(conn, root_id):
    for table in ('assets', 'metrics', 'import_batches', 'unit_day_states'):
        remaining = conn.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:root'),
                                 {'root': root_id}).scalar_one()
        unassigned = 0 if table == 'unit_day_states' else conn.execute(
            text(f'SELECT COUNT(*) FROM {table} WHERE unit_id IS NULL')).scalar_one()
        if remaining or unassigned:
            raise RuntimeError(f'Migrasi gagal: {table} masih berisi '
                               f'{remaining} milik UP3 dan {unassigned} tanpa unit')
    remaining = conn.execute(text('SELECT COUNT(*) FROM user_unit_access a JOIN users u '
       "ON u.id=a.user_id WHERE a.unit_id=:root AND u.role<>'admin'"),
       {'root': root_id}).scalar_one()
    if remaining:
        raise RuntimeError(f'Migrasi gagal: {remaining} akses non-admin masih di UP3')


def run(engine):
    """One SQL transaction, no readings/hour_records/day_states writes."""
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        _ensure_column_and_index(conn)
        migrated = conn.execute(text('SELECT 1 FROM schema_migrations WHERE version=:version'),
                                {'version': VERSION}).first()
        if migrated:
            return  # Stage 1.1 data migration is strictly once-only.
        root_id, home_id = _seed_home(conn)
        try:
            counts = _rehome_tables(conn, root_id, home_id)
            counts['unit_day_states'] = _move_day_states(conn, root_id, home_id)
            counts['user_unit_access'] = _move_nonadmin_access(conn, root_id, home_id)
        except IntegrityError as exc:
            raise RuntimeError('Migrasi legacy_home gagal karena referensi atau kunci unik '
                               'bertabrakan; perubahan dibatalkan') from exc
        _assert_root_empty(conn, root_id)
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
        conn.execute(AuditLog.__table__.insert().values(user_id=None,
            action='org_legacy_rehome', target=HOME_CODE,
            detail={'root_id': root_id, 'home_id': home_id, 'moved': counts}))
