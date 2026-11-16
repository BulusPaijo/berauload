"""Synthetic Stage 1 regression. Never uses live PostgreSQL."""
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(Path(tempfile.mkdtemp()) / "org_test.db"))
os.environ.setdefault("ADMIN_PASSWORD", "Stage-Org-Test-Password-2026")
os.environ.setdefault("UPLOAD_DIR", str(Path(tempfile.mkdtemp()) / "uploads"))
from sqlalchemy import create_engine, text, inspect
from fastapi.testclient import TestClient
from app.db import (AuditLog, DayState, HourRecord, Metric, Reading, User,
                    ImportBatch, Asset, SessionLocal)
from app.main import app
from app.modules.org_units.migrations import run as migrate
from app.modules.org_units.models import OrgUnit, UnitDayState, UserUnitAccess
from app.modules.org_units.service import (ancestors, descendants, can_read, can_write,
  OrgError, validate_creation, validate_deactivation, validate_role_key)


def login(client, name='admin', password=None):
    import os
    result = client.post('/api/auth/login', json={
        'username': name, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert result.status_code == 200, result.text
    return {'X-CSRF-Token': result.json()['csrf']}


def create(client, headers, code, level='ulp', parent=None):
    return client.post('/api/org-units', headers=headers, json={
        'code': code, 'name': code.upper(), 'level': level,
        'parent_id': parent})


def test_legacy_migration_idempotent_and_preserves_measurements():
    db_path = Path(tempfile.mkdtemp()) / 'old.db'
    eng = create_engine('sqlite:///' + str(db_path))
    with eng.begin() as c:
        for name, sql in {
            'assets': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, kind TEXT, active BOOLEAN',
            'metrics': 'id INTEGER PRIMARY KEY, code TEXT, name TEXT, unit TEXT, group_name TEXT, input_mode TEXT, asset_id INTEGER, display_order INTEGER, active BOOLEAN',
            'import_batches': 'id TEXT PRIMARY KEY, filename TEXT, sha256 TEXT, year INTEGER, month INTEGER',
            'users': 'id INTEGER PRIMARY KEY, username TEXT, role TEXT',
            'day_states': 'day DATE PRIMARY KEY, status TEXT, verified_by INTEGER, finalized_by INTEGER, updated_at DATETIME, note TEXT',
            'hour_records': 'id INTEGER PRIMARY KEY, day DATE, hour INTEGER',
            'readings': 'id INTEGER PRIMARY KEY, hour_id INTEGER, metric_id INTEGER, value NUMERIC',
        }.items():
            c.execute(text(f'CREATE TABLE {name} ({sql})'))
        c.execute(text("INSERT INTO users VALUES (1, 'legacy', 'verifier')"))
        c.execute(text("INSERT INTO assets VALUES (1,'old_asset','Old Asset','pembangkit',1)"))
        c.execute(text("INSERT INTO metrics VALUES (1,'beban_sistem_kw','Load','kW','REKAP','input',1,1,1)"))
        c.execute(text("INSERT INTO metrics VALUES (2,'daya_pasok_pembangkit_kw','Capacity','kW','REKAP','input',1,2,1)"))
        c.execute(text("INSERT INTO import_batches VALUES ('batch','a.xlsx','hash',2026,11)"))
        c.execute(text("INSERT INTO day_states VALUES ('2026-11-14','verified',1,NULL,'2026-11-14','ok')"))
        c.execute(text("INSERT INTO hour_records VALUES (1,'2026-11-14',2)"))
        c.execute(text("INSERT INTO readings VALUES (1,1,1,0)"))
    def snapshot():
        with eng.connect() as c:
            return tuple(c.execute(text(f'SELECT * FROM {t}')).all()
                         for t in ('readings', 'hour_records', 'day_states'))
    before = snapshot()
    migrate(eng)
    after1 = snapshot()
    migrate(eng)
    after2 = snapshot()
    assert before == after1 == after2
    with eng.connect() as c:
        root = c.execute(text('SELECT id,code FROM org_units')).one()
        assert root.code == 'up3_berau'
        for table in ('assets','metrics','import_batches'):
            assert c.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id=:id'),
                             {'id':root.id}).scalar() == c.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
        assert c.execute(text("SELECT role_key FROM metrics WHERE code='beban_sistem_kw'")).scalar() == 'system.load'
        assert c.execute(text("SELECT role_key FROM metrics WHERE code='daya_pasok_pembangkit_kw'")).scalar() == 'system.capacity'
        assert c.execute(text('SELECT COUNT(*) FROM unit_day_states')).scalar() == 1
        assert c.execute(text('SELECT role FROM user_unit_access WHERE user_id=1')).scalar() == 'verifier'
        assert c.execute(text("SELECT COUNT(*) FROM schema_migrations WHERE version='20261115_11_org_units_stage1'")).scalar() == 1
    eng.dispose()


def test_hierarchy_and_scope_helpers():
    u = [{'id':1,'level':'up3','parent_id':None,'active':True},
         {'id':2,'level':'ulp','parent_id':1,'active':True},
         {'id':3,'level':'kp','parent_id':2,'active':True},
         {'id':4,'level':'ulp','parent_id':1,'active':True}]
    assert descendants(1,u)==[2,4,3]
    assert ancestors(3,u)==[2,1]
    assert can_read([{'unit_id':1,'role':'admin'}],3,u)
    assert can_read([{'unit_id':2,'role':'operator'}],3,u)
    assert not can_read([{'unit_id':2,'role':'operator'}],4,u)
    assert not can_read([{'unit_id':3,'role':'operator'}],2,u)
    assert can_write([{'unit_id':2,'role':'operator'}],2,u)
    assert can_write([{'unit_id':2,'role':'operator'}],3,u)
    assert not can_write([{'unit_id':3,'role':'operator'}],2,u)
    assert not can_write([{'unit_id':2,'role':'management'}],2,u)
    import pytest
    for level,parent in [('ulp',None),('kp',u[0]),('kp',u[2]),('up3',None)]:
        with pytest.raises(OrgError):
            validate_creation(level,parent,u)
    with pytest.raises(OrgError):
        validate_deactivation(u[1],u)
    assert validate_role_key('feeder.arus_r') == 'feeder.arus_r'
    for bad in ('Legacy.Bad', 'bad..key', 'x.', '1start', 'x-y'):
        with pytest.raises(OrgError):validate_role_key(bad)


def test_api_hierarchy_csrf_access_and_audit():
    with TestClient(app) as client:
        admin=login(client)
        root=client.get('/api/org-units').json()[0]
        assert root['code']=='up3_berau'
        assert len(root['children']) == 1
        home = root['children'][0]
        assert home['code'] == 'ulp_tanjung_redeb'
        assert home['legacy_home'] and home['level'] == 'ulp' 
        assert client.post('/api/org-units',json={'code':'qa_bad','name':'QA',
                             'level':'ulp','parent_id':root['id']}).status_code==403
        assert create(client,admin,'qa_wrong','kp',root['id']).status_code == 422
        assert create(client,admin,'qa_orphan','ulp',None).status_code == 422
        assert create(client,admin,'qa_up3','up3',None).status_code == 422
        ulp=create(client,admin,'qa_ulp','ulp',root['id'])
        assert ulp.status_code==201,ulp.text
        ulp_id=ulp.json()['id']
        kp=create(client,admin,'qa_kp','kp',ulp_id)
        assert kp.status_code==201,kp.text
        kp_id=kp.json()['id']
        assert create(client,admin,'qa_nested','kp',kp_id).status_code==422
        assert client.put(f'/api/org-units/{ulp_id}/status',headers=admin,
                          json={'active':False}).status_code==422
        forbidden=client.put(f'/api/org-units/{ulp_id}',headers=admin,
                 json={'name':'Rename','display_order':1,'code':'changed'})
        assert forbidden.status_code==422,forbidden.text
        ok=client.put(f'/api/org-units/{ulp_id}',headers=admin,
                      json={'name':'Unit QA','display_order':1})
        assert ok.status_code==200
        assert ok.json()['code']=='qa_ulp'
        u=client.post('/api/users',headers=admin,json={'username':'orgqa',
          'display_name':'Organisasi QA', 'password':'Org-Test-Password-2026',
          'role':'operator', 'accesses': _qa_grants('operator')})
        assert u.status_code==200,u.text
        with TestClient(app) as viewer:
            client_headers=login(viewer,'orgqa','Org-Test-Password-2026')
            assert viewer.get('/api/org-units').status_code==200
            assert create(viewer,client_headers,'qa_forbid','kp',ulp_id).status_code==403
            assert viewer.get(f'/api/org-units/{ulp_id}/access').status_code==403
        access=client.put(f'/api/org-units/{ulp_id}/access',headers=admin,
                          json={'entries':[{'user_id':u.json()['id'],'role':'operator'}]})
        assert access.status_code==200,access.text
        assert len(client.get(f'/api/org-units/{ulp_id}/access').json())==1
        assert client.put(f'/api/org-units/{root["id"]}/status',headers=admin,
                          json={'active':False}).status_code==422
        with SessionLocal() as db:
            assert db.query(AuditLog).filter(AuditLog.action=='org_unit_create').count()>=2
            assert db.query(UserUnitAccess).filter_by(user_id=u.json()['id'],unit_id=home['id']).count()==1
            assert db.query(UserUnitAccess).filter_by(user_id=u.json()['id'],unit_id=root['id']).count()==0


def test_role_key_catalog_and_legacy_api_default():
    with TestClient(app) as client:
        admin=login(client)
        catalog=client.get('/api/catalog').json()
        assert all(a['unit_id'] is not None for a in catalog['assets'])
        assert all(m['unit_id'] is not None for m in catalog['metrics'])
        m=next(m for m in catalog['metrics'] if m['code']=='beban_sistem_kw')
        assert m['role_key']=='system.load'
        other=next(m for m in catalog['metrics'] if m['code']=='daya_pasok_pembangkit_kw')
        assert other['role_key']=='system.capacity'
        assert client.put(f'/api/metrics/{other["id"]}',headers=admin,
            json={'name':other['name'],'active':other['active'], 'role_key':'system.load'}).status_code==409
        assert client.put(f'/api/metrics/{other["id"]}',headers=admin,
            json={'name':other['name'],'active':other['active'], 'role_key':'bad..key'}).status_code==422
        assert client.put(f'/api/metrics/{other["id"]}',headers=admin,
            json={'name':other['name'],'active':other['active']}).status_code==200
        assert client.get('/api/catalog').json()['metrics'][0].get('unit_id') is not None


def test_dual_write_on_verify_finalize_reopen():
    with TestClient(app) as client:
        admin=login(client)
        day='2026-09-23'
        # beban_sistem_kw is computed/imported: synthetic reading created only in QA DB.
        with SessionLocal() as db:
            record=HourRecord(day=date.fromisoformat(day), hour=12,
                timestamp_utc=datetime(2026,9,23,4,tzinfo=timezone.utc))
            db.add(record);db.flush()
            m=db.query(Metric).filter_by(code='beban_sistem_kw').one()
            db.add(Reading(hour_id=record.id,metric_id=m.id,value=0,source='qa'))
            db.commit()
        for endpoint in ('verify','finalize','reopen'):
            result=client.post(f'/api/days/{day}/{endpoint}',headers=admin,
                               json={'reason':'QA dual-write independent'})
            assert result.status_code==200,(endpoint,result.text)
            with SessionLocal() as db:
                source=db.get(DayState,date.fromisoformat(day))
                mirror=db.query(UnitDayState).filter_by(day=date.fromisoformat(day)).one()
                assert (source.status,source.verified_by,source.finalized_by,source.note)==(
                        mirror.status,mirror.verified_by,mirror.finalized_by,mirror.note)
                assert db.query(Reading).join(HourRecord).filter(HourRecord.day==date.fromisoformat(day)).count()>0


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
