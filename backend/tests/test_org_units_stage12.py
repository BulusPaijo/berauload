"""V1.6.0 Stage 1.2: startup must never replay completed data migrations.

All records are synthetic and stored in disposable SQLite databases.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import Metric, User
from app.modules.org_units.migrations import run as migrate_stage1
from app.modules.org_units.migration_home import run as migrate_home
from app.modules.org_units.models import OrgUnit, UserUnitAccess


TABLES = ('org_units', 'assets', 'metrics', 'import_batches',
          'unit_day_states', 'user_unit_access', 'audit_logs',
          'readings', 'hour_records', 'day_states', 'schema_migrations')


def snapshot(conn, tables=TABLES):
    return {table: tuple(conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).all())
            for table in tables}


def test_setup_twice_preserves_valid_root_and_other_unit_data(monkeypatch, tmp_path):
    """Proves all four reported restart bugs stay fixed with actual setup()."""
    engine = create_engine(f'sqlite:///{tmp_path / "startup.db"}')
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', Session)
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(main, 'STAGING_DIR', tmp_path / 'uploads' / 'staging')
    monkeypatch.setenv('ADMIN_PASSWORD', 'Stage12-Test-Password-2026')
    main.setup()
    with Session() as db:
        root = db.query(OrgUnit).filter_by(level='up3').one()
        home = db.query(OrgUnit).filter_by(legacy_home=True).one()
        other = OrgUnit(code='ulp_test_other', name='ULP Other (QA)', level='ulp',
                        parent_id=root.id, active=True, display_order=1)
        db.add(other)
        computed = Metric(code='qa_up3_computed', name='UP3 QA Recap', unit='kW',
                          group_name='REKAP', input_mode='computed', unit_id=root.id)
        db.add(computed)
        user_with_conflict = User(username='qa_conflicting', display_name='QA Conflict',
                                  role='operator', password_hash='synthetic')
        only_other = User(username='qa_other_only', display_name='QA Other',
                          role='operator', password_hash='synthetic')
        db.add_all((user_with_conflict, only_other))
        db.flush()
        db.add_all((
            UserUnitAccess(user_id=user_with_conflict.id, unit_id=root.id, role='verifier'),
            UserUnitAccess(user_id=user_with_conflict.id, unit_id=home.id, role='operator'),
            UserUnitAccess(user_id=only_other.id, unit_id=other.id, role='operator'),
        ))
        db.commit()
        root_id, home_id, other_id = root.id, home.id, other.id
        conflict_id, other_user_id = user_with_conflict.id, only_other.id
    with engine.connect() as conn:
        before = snapshot(conn)
    main.setup()
    main.setup()
    with engine.connect() as conn:
        assert snapshot(conn) == before, 'Restart must not move, create or remove rows'
    with Session() as db:
        assert db.query(Metric).filter_by(code='qa_up3_computed').one().unit_id == root_id
        roles = {(r.unit_id, r.role) for r in db.query(UserUnitAccess)
                 .filter_by(user_id=conflict_id)}
        assert roles == {(root_id, 'verifier'), (home_id, 'operator')}
        assert {(r.unit_id, r.role) for r in db.query(UserUnitAccess)
                .filter_by(user_id=other_user_id)} == {(other_id, 'operator')}
    engine.dispose()


def _legacy_db(path):
    engine = create_engine(f'sqlite:///{path}')
    specs = {
        'assets': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, kind TEXT, active BOOLEAN',
        'metrics': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, unit TEXT, group_name TEXT, input_mode TEXT, asset_id INTEGER, display_order INTEGER, active BOOLEAN',
        'import_batches': 'id TEXT PRIMARY KEY, filename TEXT, sha256 TEXT, year INTEGER, month INTEGER',
        'users': 'id INTEGER PRIMARY KEY, username TEXT, role TEXT',
        'day_states': 'day DATE PRIMARY KEY, status TEXT, verified_by INTEGER, finalized_by INTEGER, updated_at DATETIME, note TEXT',
        'hour_records': 'id INTEGER PRIMARY KEY, day DATE, hour INTEGER',
        'readings': 'id INTEGER PRIMARY KEY, hour_id INTEGER, metric_id INTEGER, value NUMERIC',
        'audit_logs': 'id INTEGER PRIMARY KEY, created_at DATETIME, user_id INTEGER, action TEXT, target TEXT, detail JSON',
    }
    with engine.begin() as conn:
        for table, columns in specs.items():
            conn.execute(text(f'CREATE TABLE {table} ({columns})'))
        conn.execute(text("INSERT INTO users VALUES (1,'admin','admin'),(2,'field','operator')"))
        conn.execute(text("INSERT INTO assets VALUES (1,'legacy','Legacy','pembangkit',1)"))
        conn.execute(text("INSERT INTO metrics VALUES (1,'beban_sistem_kw','Beban','kW','REKAP','input',1,0,1)"))
        conn.execute(text("INSERT INTO metrics VALUES (2,'daya_pasok_pembangkit_kw','Mampu','kW','REKAP','input',1,1,1)"))
        conn.execute(text("INSERT INTO import_batches VALUES ('batch','historic.xlsx','checksum',2026,11)"))
        conn.execute(text("INSERT INTO day_states VALUES ('2026-11-14','verified',2,NULL,'2026-11-14','QA')"))
        conn.execute(text("INSERT INTO hour_records VALUES (1,'2026-11-14',12)"))
        conn.execute(text('INSERT INTO readings VALUES (1,1,1,0),(2,1,2,27000)'))
    return engine


@pytest.mark.parametrize('origin', ['stage4.2', 'stage1', 'stage1.1'])
def test_all_upgrade_paths_preserve_readings_and_are_once_only(origin):
    with TemporaryDirectory() as td:
        engine = _legacy_db(Path(td) / 'historical.db')
        with engine.connect() as conn:
            measurements = snapshot(conn, ('readings', 'hour_records', 'day_states'))
        if origin in ('stage1', 'stage1.1'):
            migrate_stage1(engine)
        if origin == 'stage1.1':
            migrate_home(engine)
        migrate_stage1(engine)
        migrate_home(engine)
        with engine.connect() as conn:
            assert snapshot(conn, ('readings', 'hour_records', 'day_states')) == measurements
            root = conn.execute(text("SELECT id FROM org_units WHERE level='up3'")).scalar_one()
            home = conn.execute(text("SELECT id FROM org_units WHERE legacy_home=TRUE")).scalar_one()
            for table in ('assets', 'metrics', 'import_batches', 'unit_day_states'):
                assert conn.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:id'),
                                    {'id': root}).scalar_one() == 0
                assert conn.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:id'),
                                    {'id': home}).scalar_one() > 0
            assert conn.execute(text('SELECT COUNT(*) FROM schema_migrations WHERE version=:v'),
                                {'v':'20261115_12_legacy_home_ulp_tanjung_redeb'}).scalar_one() == 1
            before_restart = snapshot(conn)
        migrate_stage1(engine)
        migrate_home(engine)
        with engine.connect() as conn:
            assert snapshot(conn) == before_restart
            assert snapshot(conn, ('readings', 'hour_records', 'day_states')) == measurements
        engine.dispose()
