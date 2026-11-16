"""V1.4.1 category CRUD, legacy preservation and permissions."""
import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_kinds_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Equipment-Kinds-2026-Strong'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, engine, Reading, Asset
from app.modules.equipment_kinds.migrations import run, VERSION
from app.modules.formulas.models import SchemaMigration


def login(client, username='admin', password=None):
    result = client.post('/api/auth/login', json={
        'username': username, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert result.status_code == 200, result.text
    return {'X-CSRF-Token': result.json()['csrf']}


def test_seed_repeat_and_custom_lifecycle():
    with TestClient(app) as client:
        head = login(client)
        before = client.get('/api/equipment-kinds').json()
        assert {'pembangkit', 'feeder', 'incoming', 'sistem', 'lain'} <= {
            item['code'] for item in before}
        with SessionLocal() as db:
            readings = db.query(Reading).count()
        created = client.post('/api/equipment-kinds', headers=head,
            json={'code': 'trafo', 'name': 'Transformator'})
        assert created.status_code == 201, created.text
        kind = created.json()
        assert client.post('/api/equipment-kinds', headers=head,
            json={'code': 'trafo', 'name': 'Transformator'}).status_code == 409
        asset = client.post('/api/assets', headers=head,
            json={'code': 'trafo_qa', 'name': 'Trafo QA', 'kind': 'trafo'})
        assert asset.status_code == 200, asset.text
        updated = client.put(f"/api/equipment-kinds/{kind['id']}", headers=head,
            json={'name': 'Transformator Daya', 'active': False})
        assert updated.status_code == 200
        assert updated.json()['code'] == 'trafo'
        assert client.post('/api/assets', headers=head,
            json={'code': 'trafo_other', 'name': 'Trafo Baru', 'kind': 'trafo'}).status_code == 422
        with SessionLocal() as db:
            assert db.query(Asset).filter_by(code='trafo_qa').one().kind == 'trafo'
            assert db.query(Reading).count() == readings
        run(engine); run(engine)
        with SessionLocal() as db:
            assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        assert len([x for x in client.get('/api/equipment-kinds').json() if x['code']=='trafo']) == 1


def test_kind_permissions_and_bad_inputs():
    with TestClient(app) as client:
        head = login(client)
        assert client.post('/api/equipment-kinds', headers=head,
            json={'code':'_bad', 'name':'Tidak Valid'}).status_code == 422
        assert client.post('/api/assets', headers=head,
            json={'code':'bad_kind_asset','name':'Tidak Valid','kind':'random'}).status_code == 422
        created = client.post('/api/users', headers=head, json={
            'username':'kinds_viewer', 'display_name':'Viewer Jenis',
            'password':'Test-Viewer-Kinds-2026-Strong','role':'management', 'accesses': _qa_grants('management')})
        assert created.status_code == 200
        with TestClient(app) as viewer:
            v = login(viewer, 'kinds_viewer', 'Test-Viewer-Kinds-2026-Strong')
            assert viewer.get('/api/equipment-kinds').status_code == 200
            assert viewer.post('/api/equipment-kinds', headers=v,
                json={'code':'new_kind','name':'Kategori Baru'}).status_code == 403
            assert viewer.put('/api/equipment-kinds/1', headers=v,
                json={'name':'Ubah','active':True}).status_code == 403


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
