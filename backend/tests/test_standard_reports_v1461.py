"""Standard report selector: isolated SQLite and deterministic hourly readings."""
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_standard_reports_'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(root / 'qa.db'))
os.environ.setdefault('UPLOAD_DIR', str(root / 'uploads'))
os.environ.setdefault('ADMIN_PASSWORD', 'Standard-Report-QA-Password-12345')

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Metric, HourRecord, Reading, engine
from app.modules.standard_reports.migrations import VERSION, run as migrate
from app.modules.standard_reports.models import StandardReportSelection
from app.modules.formulas.models import SchemaMigration
from app.modules.standard_reports.service import growth_pct

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client, username='admin', password=None):
    response = client.post('/api/auth/login', json={
        'username': username, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


def seed():
    with SessionLocal() as db:
        metric = db.query(Metric).filter_by(code=LOAD).one()
        if db.query(HourRecord.id).filter_by(day=date(2025, 3, 12), hour=0).first():
            return
        for year, readings in ((2025, [(0, 0), (1, 40)]),
                               (2026, [(0, 0), (1, 60)])):
            for hour, val in readings:
                record = HourRecord(day=date(year, 3, 12), hour=hour,
                    timestamp_utc=datetime(year, 3, 11, 16+hour, tzinfo=timezone.utc))
                db.add(record)
                db.flush()
                db.add(Reading(hour_id=record.id, metric_id=metric.id,
                               value=Decimal(val), source='qa'))
        db.commit()


def test_legacy_and_new_aggregation():
    with TestClient(app) as client:
        headers = login(client)
        seed()
        url = '/api/compare?year_a=2025&year_b=2026&metric=' + LOAD
        legacy = client.get(url)
        assert legacy.status_code == 200
        march = legacy.json()['data'][2]
        assert march['a']['peak'] == 40 and march['b']['peak'] == 60
        assert march['peak_growth_pct'] == 50
        assert march['growth_pct'] == 50
        assert not march['comparable']
        assert legacy.json()['data'][0]['value_a'] is None
        assert len(legacy.json()['data']) == 12
        average = client.get(url + '&aggregate=avg')
        assert average.status_code == 200
        assert average.json()['data'][2]['value_a'] == 20
        assert average.json()['data'][2]['value_b'] == 30
        assert average.json()['data'][2]['growth_pct'] == 50
        minimum = client.get(url + '&aggregate=min')
        assert minimum.json()['data'][2]['value_a'] == 0
        assert minimum.json()['data'][2]['value_b'] == 0
        assert minimum.json()['data'][2]['growth_pct'] is None
        assert client.get(url + '&aggregate=sum').status_code == 422
        assert client.get(url.replace(LOAD, 'unknown_metric')).status_code == 404
        assert client.get(url.replace('2025', '2019')).status_code == 422


def test_preference_scope_auth_and_reset():
    with TestClient(app) as admin:
        h = login(admin)
        state = admin.get('/api/standard-reports')
        assert state.status_code == 200
        assert state.json()['effective'] == {'metric_code': LOAD, 'aggregation': 'max'}
        assert state.json()['personal'] is None
        assert admin.put('/api/standard-reports/system', headers={'X-CSRF-Token': 'bad'},
                         json={'metric_code': CAP, 'aggregation': 'avg'}).status_code == 403
        assert admin.put('/api/standard-reports/system', headers=h,
                         json={'metric_code': LOAD, 'aggregation': 'sum'}).status_code == 422
        assert admin.put('/api/standard-reports/system', headers=h,
                         json={'metric_code': 'not_a_metric', 'aggregation': 'max'}).status_code == 422
        assert admin.put('/api/standard-reports/system', headers=h,
                         json={'metric_code': 'daya_mampu_sistem_kw', 'aggregation': 'max'}).status_code == 422
        saved = admin.put('/api/standard-reports/system', headers=h,
                          json={'metric_code': CAP, 'aggregation': 'avg'})
        assert saved.status_code == 200
        assert saved.json()['system'] == {'metric_code': CAP, 'aggregation': 'avg'}
        user = admin.post('/api/users', headers=h, json={
            'username': 'viewerstd1461', 'display_name': 'Viewer Std', 'role': 'management', 'accesses': _qa_grants('management'),
            'password': 'Viewer-Standard-Password-2026'})
        assert user.status_code == 200, user.text
        with TestClient(app) as viewer:
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            assert viewer.get('/api/standard-reports').status_code == 401
            uh = login(viewer, 'viewerstd1461', 'Viewer-Standard-Password-2026')
            assert viewer.get('/api/standard-reports', headers=home).json()['effective']['metric_code'] == CAP
            assert viewer.put('/api/standard-reports/system', headers={**uh,**home},
                json={'metric_code': LOAD, 'aggregation': 'max'}).status_code == 403
            assert viewer.put('/api/standard-reports/mine', headers={**uh,**home},
                json={'metric_code': LOAD, 'aggregation': 'min'}).status_code == 403
            assert viewer.delete('/api/standard-reports/mine',headers={**uh,**home}).status_code == 403
            assert viewer.get('/api/standard-reports',headers=home).json()['effective']['metric_code'] == CAP


def test_migration_idempotency():
    with TestClient(app) as client:
        login(client)
        migrate(engine)
        migrate(engine)
        with SessionLocal() as db:
            assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
            assert db.query(StandardReportSelection).filter_by(scope='system').count() <= 1


def test_growth_edge_cases():
    assert growth_pct(None, 10) is None
    assert growth_pct(10, None) is None
    assert growth_pct(0, 10) is None
    assert growth_pct(100, 100) == 0
    assert growth_pct(100, 110) == 10


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
