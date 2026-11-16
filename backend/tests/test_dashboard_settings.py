"""Dashboard parameter defaults: isolated DB, no SCADA/external data."""
import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_chart_settings_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Dashboard-Password-12345678'

from fastapi.testclient import TestClient
from sqlalchemy import func
from app.db import SessionLocal
from app.main import app
from app.modules.dashboard_settings.migrations import VERSION, run as migrate
from app.modules.dashboard_settings.models import DashboardChartSettings
from app.modules.formulas.models import SchemaMigration


CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def admin_login(client):
    r = client.post('/api/auth/login', json={
        'username': 'admin', 'password': os.environ['ADMIN_PASSWORD'],
    })
    assert r.status_code == 200, r.text
    return {'X-CSRF-Token': r.json()['csrf']}


def test_chart_defaults_permissions_and_validation():
    with TestClient(app) as admin:
        headers = admin_login(admin)
        settings = admin.get('/api/dashboard-charts').json()
        assert settings['effective'] == [CAP, LOAD]
        assert settings['system'] == [CAP, LOAD]
        assert settings['source'] == 'system'
        assert settings['personal'] is None

        assert admin.put('/api/dashboard-charts/system', json={
            'metric_codes': [CAP, 'frequency_hz']}, headers=headers).status_code == 422
        assert admin.put('/api/dashboard-charts/system', json={
            'metric_codes': ['daya_mampu_sistem_kw']}, headers=headers).status_code == 422
        assert admin.put('/api/dashboard-charts/system', json={
            'metric_codes': [CAP, CAP]}, headers=headers).status_code == 422
        assert admin.put('/api/dashboard-charts/system', json={
            'metric_codes': []}, headers=headers).status_code == 422
        assert admin.put('/api/dashboard-charts/system', json={
            'metric_codes': [CAP]}, headers={'X-CSRF-Token': 'bad'}).status_code == 403

        saved = admin.put('/api/dashboard-charts/system', json={
            'metric_codes': [CAP, LOAD]}, headers=headers)
        assert saved.status_code == 200, saved.text
        assert admin.put('/api/dashboard-charts/mine', json={
            'metric_codes': ['pltu_lati_cb33_kw']}, headers=headers).status_code == 200
        assert admin.get('/api/dashboard-charts').json()['effective'] == ['pltu_lati_cb33_kw']

        created = admin.post('/api/users', json={
            'username': 'viewerchart', 'display_name': 'Viewer Chart',
            'password': 'ViewerChart-Password-123456', 'role': 'management', 'accesses': _qa_grants('management'),
        }, headers=headers)
        assert created.status_code == 200, created.text

        with TestClient(app) as viewer:
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            assert viewer.get('/api/dashboard-charts').status_code == 401
            login = viewer.post('/api/auth/login', json={
                'username': 'viewerchart', 'password': 'ViewerChart-Password-123456',
            })
            assert login.status_code == 200
            viewer_headers = {**home,'X-CSRF-Token': login.json()['csrf']}
            assert viewer.get('/api/dashboard-charts',headers=home).json()['effective'] == [CAP, LOAD]
            assert viewer.put('/api/dashboard-charts/system', json={
                'metric_codes': [LOAD]}, headers=viewer_headers).status_code == 403
            # Stage 4b: even user-scoped configuration is admin-managed.
            assert viewer.put('/api/dashboard-charts/mine', json={
                'metric_codes': [LOAD]}, headers=viewer_headers).status_code == 403
            assert viewer.delete('/api/dashboard-charts/mine', headers=viewer_headers).status_code == 403
            assert viewer.get('/api/dashboard-charts',headers=home).json()['effective'] == [CAP, LOAD]

        assert admin.delete('/api/dashboard-charts/mine', headers=headers).status_code == 200
        assert admin.get('/api/dashboard-charts').json()['effective'] == [CAP, LOAD]


def test_migration_idempotent_existing_formula_unchanged():
    from app.db import engine
    migrate(engine)
    migrate(engine)
    with SessionLocal() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        assert db.query(DashboardChartSettings).filter_by(scope='system').count() == 1
        assert db.query(DashboardChartSettings).filter_by(scope='user').count() == 0
        assert db.query(func.count(DashboardChartSettings.id)).scalar() == 1


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
