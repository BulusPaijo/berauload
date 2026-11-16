"""Stage 1.1 tests use only synthetic temporary SQLite databases."""
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import tempfile
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(Path(tempfile.mkdtemp()) / "org_home_test.db"))
os.environ.setdefault("ADMIN_PASSWORD", "Stage-Home-Test-Password-2026")
os.environ.setdefault("UPLOAD_DIR", str(Path(tempfile.mkdtemp()) / "uploads"))
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import pytest

from app.db import Asset, Metric, User, DayState, ImportBatch, SessionLocal
from app.modules.org_units.migrations import run as stage1
from app.modules.org_units.migration_home import run as stage11
from app.modules.org_units.repository import home_unit, root, attach_new_user, mirror_day_state
from app.modules.org_units.models import OrgUnit, UnitDayState, UserUnitAccess


LEGACY_SQL = {
    'assets': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, kind TEXT, active BOOLEAN',
    'metrics': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, unit TEXT, group_name TEXT, input_mode TEXT, asset_id INTEGER, display_order INTEGER, active BOOLEAN',
    'import_batches': 'id TEXT PRIMARY KEY, filename TEXT, sha256 TEXT, year INTEGER, month INTEGER',
    'users': 'id INTEGER PRIMARY KEY, username TEXT, role TEXT',
    'day_states': 'day DATE PRIMARY KEY, status TEXT, verified_by INTEGER, finalized_by INTEGER, updated_at DATETIME, note TEXT',
    'hour_records': 'id INTEGER PRIMARY KEY, day DATE, hour INTEGER',
    'readings': 'id INTEGER PRIMARY KEY, hour_id INTEGER, metric_id INTEGER, value NUMERIC',
    'audit_logs': 'id INTEGER PRIMARY KEY, created_at DATETIME, user_id INTEGER, action TEXT, target TEXT, detail JSON',
}


def _legacy_engine(path):
    eng = create_engine('sqlite:///' + str(path))
    with eng.begin() as c:
        for name, cols in LEGACY_SQL.items():
            c.execute(text(f'CREATE TABLE {name} ({cols})'))
        c.execute(text("INSERT INTO users VALUES (1,'admin','admin'),(2,'operator','operator')"))
        c.execute(text("INSERT INTO assets VALUES (1,'old_asset','Old','pembangkit',1)"))
        c.execute(text("INSERT INTO metrics VALUES (1,'beban_sistem_kw','Load','kW','REKAP','input',1,1,1)"))
        c.execute(text("INSERT INTO metrics VALUES (2,'daya_pasok_pembangkit_kw','Capacity','kW','REKAP','input',1,2,1)"))
        c.execute(text("INSERT INTO import_batches VALUES ('b1','a.xlsx','hash',2026,11)"))
        c.execute(text("INSERT INTO day_states VALUES ('2026-11-14','verified',2,NULL,'2026-11-14','ok')"))
        c.execute(text("INSERT INTO hour_records VALUES (1,'2026-11-14',2)"))
        c.execute(text("INSERT INTO readings VALUES (1,1,1,0),(2,1,2,27.5)"))
    return eng


def _snapshot(conn):
    return tuple(tuple(conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).all())
                 for table in ('readings', 'hour_records', 'day_states'))


def _assert_owner(conn):
    roots = conn.execute(text("SELECT id FROM org_units WHERE level='up3'")).scalars().all()
    homes = conn.execute(text("SELECT id FROM org_units WHERE legacy_home=TRUE")).scalars().all()
    assert len(roots) == len(homes) == 1
    root_id, home_id = roots[0], homes[0]
    assert root_id != home_id
    assert conn.execute(text('SELECT code FROM org_units WHERE id=:id'), {'id':home_id}).scalar_one() == 'ulp_tanjung_redeb'
    for table in ('assets','metrics','import_batches','unit_day_states'):
        assert conn.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:home'),
                            {'home':home_id}).scalar_one() == conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one()
        assert conn.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:root'), {'root':root_id}).scalar_one() == 0
    assert conn.execute(text("SELECT role_key FROM metrics WHERE code='beban_sistem_kw'")).scalar_one() == 'system.load'
    assert conn.execute(text("SELECT role_key FROM metrics WHERE code='daya_pasok_pembangkit_kw'")).scalar_one() == 'system.capacity'
    assert conn.execute(text("SELECT unit_id FROM user_unit_access WHERE user_id=1")).scalar_one() == root_id
    assert conn.execute(text("SELECT unit_id FROM user_unit_access WHERE user_id=2")).scalar_one() == home_id
    return root_id, home_id


@pytest.mark.parametrize('origin', ['stage4.2', 'stage1'])
def test_both_upgrade_paths_preserve_measurements_and_are_idempotent(origin):
    with TemporaryDirectory() as td:
        engine = _legacy_engine(Path(td)/'legacy.db')
        with engine.connect() as conn:
            before = _snapshot(conn)
        stage1(engine)
        if origin == 'stage1':
            stage1(engine)
        stage11(engine)
        with engine.connect() as conn:
            assert _snapshot(conn) == before
            _assert_owner(conn)
            after = [tuple(conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).all())
                     for table in ('org_units','assets','metrics','import_batches','unit_day_states','user_unit_access','audit_logs')]
        stage1(engine)
        stage11(engine)
        with engine.connect() as conn:
            assert _snapshot(conn) == before
            _assert_owner(conn)
            assert after == [tuple(conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).all())
                             for table in ('org_units','assets','metrics','import_batches','unit_day_states','user_unit_access','audit_logs')]
            assert conn.execute(text('SELECT COUNT(*) FROM schema_migrations WHERE version=:v'),
                 {'v':'20261115_12_legacy_home_ulp_tanjung_redeb'}).scalar_one() == 1
        engine.dispose()


def test_unique_home_and_root_db_constraints():
    with TemporaryDirectory() as td:
        eng = _legacy_engine(Path(td)/'legacy.db')
        stage1(eng); stage11(eng)
        with pytest.raises(IntegrityError):
            with eng.begin() as conn:
                conn.execute(text("INSERT INTO org_units (code,name,level,parent_id,active,legacy_home,display_order,created_at) "
                    "VALUES ('ulp_second','Second','ulp',1,TRUE,TRUE,0,CURRENT_TIMESTAMP)"))
        with pytest.raises(IntegrityError):
            with eng.begin() as conn:
                conn.execute(text("INSERT INTO org_units (code,name,level,parent_id,active,legacy_home,display_order,created_at) "
                    "VALUES ('up3_second','Second','up3',NULL,TRUE,FALSE,0,CURRENT_TIMESTAMP)"))
        eng.dispose()


def test_new_legacy_records_attach_to_home_unit():
    # Exercise the SQLAlchemy repository helpers using full ORM-compatible schema.
    from app.db import Base
    from sqlalchemy.orm import sessionmaker
    from app.modules.org_units.migrations import precreate
    with TemporaryDirectory() as td:
        eng = create_engine('sqlite:///' + str(Path(td)/'fresh.db'))
        precreate(eng)
        Base.metadata.create_all(eng)
        stage1(eng); stage11(eng)
        Session = sessionmaker(bind=eng, expire_on_commit=False)
        with Session() as db:
            home = home_unit(db)
            assert root(db).id != home.id
            db.add(Asset(code='qa_asset',name='QA Asset',kind='pembangkit',unit_id=home.id))
            db.add(Metric(code='qa_metric',name='QA Metric',unit='kW',group_name='REKAP',
                          input_mode='input',unit_id=home.id))
            db.add(ImportBatch(id='qa-batch',filename='a.xlsx',sha256='x'*64,year=2026,
                               month=11,unit_id=home.id))
            nonadmin=User(username='qa-operator',display_name='QA Operator',role='operator',password_hash='x')
            admin=User(username='qa-admin',display_name='QA Admin',role='admin',password_hash='x')
            db.add_all([nonadmin,admin]);db.flush()
            attach_new_user(db,nonadmin);attach_new_user(db,admin)
            state=DayState(day=date(2026,11,13),status='draft')
            db.add(state);db.flush();mirror_day_state(db,state)
            db.commit()
            assert db.query(UnitDayState).filter_by(day=state.day).one().unit_id == home.id
            assert db.query(UserUnitAccess).filter_by(user_id=nonadmin.id).one().unit_id == home.id
            assert db.query(UserUnitAccess).filter_by(user_id=admin.id).one().unit_id == root(db).id
        eng.dispose()


def test_legacy_api_new_asset_metric_user_and_dashboard_unchanged_on_replay():
    """Existing API still uses global permissions and a single operational scope."""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import engine as application_engine
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={
            'username':os.getenv('ADMIN_USERNAME','admin'),
            'password':os.environ['ADMIN_PASSWORD']})
        assert login.status_code == 200, login.text
        headers = {'X-CSRF-Token':login.json()['csrf']}
        dashboard = '/api/dashboard?year=2026&month=11'
        compare = '/api/monitoring/capacity-vs-load?start=2026-11-01&end=2026-11-14&granularity=day'
        before = (client.get(dashboard).json(), client.get(compare).json())
        asset = client.post('/api/assets', headers=headers, json={
            'code':'qa_stage11_asset','name':'QA Stage 1.1 Asset','kind':'pembangkit'})
        assert asset.status_code == 200, asset.text
        metric = client.post('/api/metrics', headers=headers, json={
            'code':'qa_stage11_kw','name':'QA Stage 1.1 Metric','unit':'kW',
            'group_name':'PEMBANGKIT', 'asset_id':asset.json()['id']})
        assert metric.status_code == 200, metric.text
        new_user = client.post('/api/users', headers=headers, json={
            'username':'stage11_qaman', 'display_name':'QA Stage 1.1 Management',
            'password':'Stage11-QA-Password-123456', 'role':'management', 'accesses': _qa_grants('management')})
        assert new_user.status_code == 200, new_user.text
        with SessionLocal() as db:
            home = home_unit(db)
            assert db.get(Asset,asset.json()['id']).unit_id == home.id
            assert db.get(Metric,metric.json()['id']).unit_id == home.id
            # Stage 4a: UP3 management is read-only with inherited visibility.
            from app.modules.org_units.repository import root
            assert db.query(UserUnitAccess).filter_by(user_id=new_user.json()['id']).one().unit_id == root(db).id
        stage1(application_engine)
        stage11(application_engine)
        assert (client.get(dashboard).json(),client.get(compare).json()) == before


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
