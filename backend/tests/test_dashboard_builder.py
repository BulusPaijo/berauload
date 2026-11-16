"""Regression: layouts isolated from operational readings, safe default/permissions."""
import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_dashboard_builder_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Dashboard-Builder-Password-2026'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, engine, Reading
from app.modules.dashboard_builder.migrations import VERSION, run as migrate
from app.modules.dashboard_builder.models import DashboardLayout
from app.modules.formulas.models import SchemaMigration

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client, username='admin', password=None):
    password = password or os.environ['ADMIN_PASSWORD']
    result = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert result.status_code == 200, result.text
    return {'X-CSRF-Token': result.json()['csrf']}


def payload(codes=None, kind='line', aggregation='avg'):
    return {'id': 'p-1', 'title': 'Grafik Operasi', 'source': 'metric', 'kind': kind,
            'metric_codes': codes or [CAP, LOAD], 'source_id': None,
            'aggregation': aggregation, 'w': 12, 'h': 2}


def test_seed_and_create_version_lock():
    with TestClient(app) as client:
        headers = login(client)
        initial = client.get('/api/dashboard-builder').json()
        assert initial['effective_default_id'] is not None
        assert initial['system_default_id'] is not None
        first = client.post('/api/dashboard-builder', headers=headers, json={
            'name': 'Dashboard Analis', 'scope': 'personal', 'panels': [payload()]})
        assert first.status_code == 201, first.text
        layout = first.json()
        assert layout['owner_id'] > 0 and layout['scope'] == 'personal'
        edited = client.put(f"/api/dashboard-builder/{layout['id']}", headers=headers, json={
            'name': 'Dashboard Analis V2', 'description': 'Custom',
            'panels': [payload()], 'expected_version': 1})
        assert edited.status_code == 200 and edited.json()['version'] == 2
        stale = client.put(f"/api/dashboard-builder/{layout['id']}", headers=headers, json={
            'name': 'Stale', 'panels': [], 'expected_version': 1})
        assert stale.status_code == 409
        assert client.get(f"/api/dashboard-builder/{layout['id']}").json()['name'] == 'Dashboard Analis V2'
        assert client.post(f"/api/dashboard-builder/{layout['id']}/default", headers=headers).status_code == 200
        assert client.get('/api/dashboard-builder').json()['effective_default_id'] == layout['id']


def test_validation_rejects_invalid_metric_sources_and_bad_csrf():
    with TestClient(app) as client:
        headers=login(client)
        def create(panel):
            return client.post('/api/dashboard-builder',headers=headers,
                               json={'name':'Uji Validasi','panels':[panel]})
        assert create(payload([CAP,'frequency_hz'])).status_code == 422
        assert create(payload([CAP,LOAD],aggregation='peak')).status_code == 422
        assert create(payload([CAP,LOAD,'pltu_lati_cb33_kw'])).status_code == 422
        assert create(payload([LOAD,LOAD])).status_code == 422
        assert create(payload(['daya_mampu_sistem_kw'])).status_code == 422
        missing = payload([LOAD]); missing['source']='historical'; missing['metric_codes']=[];missing['source_id']=9999
        assert create(missing).status_code == 422
        assert client.post('/api/dashboard-builder', headers={'X-CSRF-Token':'invalid'},
                           json={'name':'No CSRF'}).status_code == 403


def test_permissions_duplication_and_archive():
    """Stage 4b: viewing home config requires explicitly selecting that unit."""
    from app.modules.org_units.repository import home_unit
    with TestClient(app) as admin:
        a=login(admin)
        created=admin.post('/api/users',headers=a,json={
            'username':'dashview14','display_name':'View User V14',
            'password':'Dashboard-Viewer-2026-Strong', 'role':'management', 'accesses': _qa_grants('management')})
        assert created.status_code == 200, created.text
        sys_id=admin.get('/api/dashboard-builder').json()['system_default_id']
        with SessionLocal() as db:
            home={'X-Unit-Id':str(home_unit(db).id)}
        with TestClient(app) as viewer:
            v=login(viewer,'dashview14','Dashboard-Viewer-2026-Strong')
            assert viewer.get(f'/api/dashboard-builder/{sys_id}').status_code == 404
            assert viewer.get(f'/api/dashboard-builder/{sys_id}',headers=home).status_code == 200
            assert viewer.post('/api/dashboard-builder',headers={**v,**home},
                json={'name':'Dilarang Sistem','scope':'system'}).status_code == 403
            assert viewer.post(f'/api/dashboard-builder/{sys_id}/default',
                               headers={**v,**home}).status_code == 403
            assert viewer.post(f'/api/dashboard-builder/{sys_id}/duplicate',
                               headers={**v,**home}).status_code == 403
            assert viewer.post(f'/api/dashboard-builder/{sys_id}/archive',
                               headers={**v,**home}).status_code == 403
        assert admin.post(f'/api/dashboard-builder/{sys_id}/archive',headers=a).status_code == 409


def test_migration_repeat_and_data_not_written():
    migrate(engine);migrate(engine)
    with SessionLocal() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count()==1
        assert db.query(DashboardLayout).filter_by(scope='system',archived=False).count()>=1
        before=db.query(Reading).count()
    with TestClient(app) as client:
        h=login(client)
        result=client.post('/api/dashboard-builder',headers=h,
            json={'name':'Hanya Layout','scope':'personal','panels':[payload([LOAD],kind='stat')]})
        assert result.status_code==201,result.text
    with SessionLocal() as db:
        assert db.query(Reading).count()==before


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
