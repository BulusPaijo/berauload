"""V1.2.1 + V1.3.0: revision integrity, approvals, missingness, audit, migration."""
import os
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile

base = Path(tempfile.mkdtemp(prefix='berauload_ruleqa_'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(base / 'qa.db'))
os.environ.setdefault('UPLOAD_DIR', str(base / 'uploads'))
os.environ.setdefault('ADMIN_PASSWORD', 'Historical-QA-Password-12345678')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select
from app.main import app
from app.db import HourRecord, Reading, Metric, SessionLocal
from app.modules.engineering.service import classify, evaluate_sample, evaluate_history
from app.modules.historical.migrations import run as historical_migrate
from app.modules.historical.models import HistoricalRevision
from app.modules.engineering.models import EngineeringRuleRevision

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client):
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200, r.text
    return {'X-CSRF-Token': r.json()['csrf']}


def historical(code='rule_hist_cadangan'):
    return {'code': code, 'name': 'Cadangan', 'expression': f'{CAP} - {LOAD}',
            'unit': 'kW', 'aggregation': 'AVG', 'resolution': 'day', 'mode': 'period',
            'moving_days': 7, 'hour_start': 18, 'hour_end': 18}


def rule(code='rule_cadangan_v13'):
    return {'code': code, 'name': 'Cadangan Daya', 'expression': f'{CAP} - {LOAD}',
            'unit': 'kW', 'direction': 'below', 'warning_threshold': 5000,
            'critical_threshold': 1000, 'effective_from': '2026-01-01',
            'reference_note': 'Batas contoh QA, bukan referensi teknis resmi'}


def seed(day):
    with SessionLocal() as db:
        ids = {m.code: m.id for m in db.query(Metric).filter(Metric.code.in_([CAP, LOAD]))}
        for hour, load_value in [(17, 40000), (18, 45000), (19, 49000)]:
            rec = HourRecord(day=day, hour=hour,
                             timestamp_utc=datetime(day.year, day.month, day.day,
                                                    hour - 8, tzinfo=timezone.utc))
            db.add(rec); db.flush()
            db.add_all([Reading(hour_id=rec.id, metric_id=ids[CAP], value=50000, source='qa'),
                        Reading(hour_id=rec.id, metric_id=ids[LOAD], value=load_value, source='qa')])
        db.commit()


def test_boundaries_missing_zero_and_overload():
    assert classify(5, 'below', 10, 5) == 'critical'
    assert classify(10, 'below', 10, 5) == 'warning'
    assert classify(11, 'below', 10, 5) == 'normal'
    assert classify(-1, 'below', 10, 5) == 'critical'
    assert classify(0, 'above', 90, 100) == 'normal'
    assert classify(100, 'above', 90, 100) == 'critical'
    assert classify(None, 'below', 10, 5) == 'no_data'
    spec = {**rule(), 'effective_from': date(2026, 1, 1)}
    assert evaluate_sample(spec, {CAP: 100})['status'] == 'no_data'
    assert evaluate_sample(spec, {CAP: 100, LOAD: 200})['status'] == 'critical'
    result = evaluate_history(spec, [(date(2026, 11, 1), 18, CAP, 5000)],
                              date(2026, 11, 1), date(2026, 11, 1))
    assert result['valid_hours'] == 0
    assert result['missing_or_invalid_hours'] == 24
    assert result['status_counts']['normal'] == 0


def test_historical_revision_archive_and_original_readings():
    with TestClient(app) as client:
        headers = login(client)
        seed(date(2026, 10, 23))
        entry = historical()
        created = client.post('/api/historical-calculations', json=entry, headers=headers)
        assert created.status_code == 201, created.text
        id = created.json()['id']
        path = f'/api/historical-calculations/{id}/run?start=2026-10-23&end=2026-10-23'
        assert client.get(path).json()['data'][0]['value'] == 5000
        assert client.post(f'/api/historical-calculations/{id}/revisions',
                           json={**entry, 'expression': LOAD, 'expected_version': 1,
                                 'reason': 'Test revisi formula'}, headers=headers).status_code == 201
        assert client.get(path).json()['data'][0]['value'] == 45000
        old = client.get(path + '&version=1')
        assert old.json()['evaluated_version'] == 1
        assert old.json()['data'][0]['value'] == 5000
        assert client.post(f'/api/historical-calculations/{id}/revisions',
                           json={**entry, 'expected_version': 1, 'reason': 'Revisi usang'},
                           headers=headers).status_code == 409
        assert client.patch(f'/api/historical-calculations/{id}/archive',
                            json={'archived': True, 'reason': 'Tidak digunakan lagi'},
                            headers=headers).status_code == 200
        assert client.get(path).status_code == 409
        assert client.get(path + '&version=1').status_code == 200
        assert client.patch(f'/api/historical-calculations/{id}/archive',
                            json={'archived': False, 'reason': 'Diperlukan kembali'},
                            headers=headers).status_code == 200
        with SessionLocal() as db:
            assert db.query(HistoricalRevision).filter_by(definition_id=id).count() == 2
            assert db.query(Reading).filter(Reading.source == 'qa').count() == 6


def test_engineering_approval_review_history_revision():
    with TestClient(app) as client:
        headers = login(client)
        seed(date(2026, 10, 24))
        spec = rule()
        bad = {**spec, 'critical_threshold': 7000}
        assert client.post('/api/engineering-rules', json=bad, headers=headers).status_code == 422
        assert client.post('/api/engineering-rules', json=spec).status_code == 403
        p = client.post('/api/engineering-rules/preview', json={**spec,
             'samples': {CAP: 50000, LOAD: 49000}}, headers=headers)
        assert p.status_code == 200, p.text
        assert p.json()['result']['status'] == 'critical'
        create = client.post('/api/engineering-rules', json=spec, headers=headers)
        assert create.status_code == 201, create.text
        id = create.json()['id']
        assert create.json()['status'] == 'draft'
        path = f'/api/engineering-rules/{id}/history?start=2026-10-24&end=2026-10-24'
        assert client.get(path).status_code == 409
        assert client.post(f'/api/engineering-rules/{id}/activate',
                           json={'reason': 'Disetujui untuk simulasi QA'}, headers=headers).status_code == 200
        report = client.get(path)
        assert report.status_code == 200, report.text
        doc = report.json()
        assert doc['valid_hours'] == 3
        assert doc['missing_or_invalid_hours'] == 21
        assert doc['status_counts'] == {'normal': 1, 'warning': 1, 'critical': 1}
        assert doc['advisory_only'] is True
        rev = client.post(f'/api/engineering-rules/{id}/revisions', json={**spec,
            'expected_version': 1, 'warning_threshold': 6000,
            'reason': 'Revisi kebutuhan simulasi'}, headers=headers)
        assert rev.status_code == 201, rev.text
        assert rev.json()['status'] == 'draft'
        assert client.get(path).status_code == 409
        assert client.get(path + '&version=1').status_code == 200
        assert client.post(f'/api/engineering-rules/{id}/activate',
                           json={'reason': 'Setelah pemeriksaan ulang'}, headers=headers).status_code == 200
        assert client.post(f'/api/engineering-rules/{id}/archive',
                           json={'reason': 'Aturan tidak digunakan'}, headers=headers).status_code == 200
        with SessionLocal() as db:
            assert db.query(EngineeringRuleRevision).filter_by(rule_id=id).count() == 2


def test_idempotent_migrate_old_historical_table():
    path = base / 'legacy_120.db'
    engine = create_engine('sqlite:///' + str(path))
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE historical_definitions (
            id INTEGER PRIMARY KEY, code VARCHAR(90) UNIQUE NOT NULL, name VARCHAR(180) NOT NULL,
            expression TEXT NOT NULL, unit VARCHAR(12) NOT NULL, aggregation VARCHAR(12) NOT NULL,
            resolution VARCHAR(12) NOT NULL, mode VARCHAR(16) NOT NULL,
            moving_days INTEGER NOT NULL, hour_start INTEGER NOT NULL,
            hour_end INTEGER NOT NULL, version INTEGER NOT NULL,
            created_by INTEGER NULL, created_at TIMESTAMP NULL)'''))
        conn.execute(text("""INSERT INTO historical_definitions
            (id,code,name,expression,unit,aggregation,resolution,mode,moving_days,hour_start,hour_end,version)
            VALUES (1,'old_rule','Formula Lama','1+2','kW','AVG','month','period',7,0,23,1)"""))
    historical_migrate(engine)
    historical_migrate(engine)
    with engine.connect() as conn:
        rev = conn.execute(select(HistoricalRevision.snapshot)).scalar_one()
        assert rev['expression'] == '1+2'
        assert conn.execute(select(HistoricalRevision.id)).all() == [(1,)]
        assert conn.execute(text('SELECT archived FROM historical_definitions')).scalar() == 0
