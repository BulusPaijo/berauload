"""V1.2 historical formulas: pure tests + isolated API/DB tests."""
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

base = Path(tempfile.mkdtemp(prefix='berauload_historical_'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(base / 'qa.db'))
os.environ.setdefault('UPLOAD_DIR', str(base / 'uploads'))
os.environ.setdefault('ADMIN_PASSWORD', 'Historical-QA-Password-12345678')

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import HourRecord, Reading, Metric, SessionLocal, engine
from app.modules.historical.migrations import VERSION, run as migration
from app.modules.formulas.engine import FormulaError
from app.modules.formulas.models import SchemaMigration
from app.modules.historical.service import compute, valid_definition, validate_range

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def config(**changes):
    return {
        'expression': f'{CAP} - {LOAD}', 'unit': 'kW', 'aggregation': 'AVG',
        'resolution': 'day', 'mode': 'period', 'moving_days': 7,
        'hour_start': 18, 'hour_end': 18, **changes,
    }


def rows(day, a, b, hour=18):
    return [(day, hour, CAP, a), (day, hour, LOAD, b)]


def test_paired_hours_zero_missing_and_over_100():
    start = date(2026, 4, 1)
    samples = rows(start, 100, 0, 18) + rows(start, 100, 110, 19)
    rule = config(expression=f'({LOAD} / {CAP}) * 100', unit='%',
                  aggregation='MAX', hour_start=18, hour_end=20)
    assert valid_definition(rule, {CAP: 'kW', LOAD: 'kW'})
    result = compute(rule, samples, start, start)
    assert result['data'][0]['value'] == 110
    assert result['data'][0]['count'] == 2
    assert result['data'][0]['expected'] == 3
    assert result['data'][0]['complete'] is False
    assert result['data'][0]['coverage_pct'] == 66.67
    assert result['skipped_incomplete_hours'] == 0
    missing = compute(rule, [(start, 18, CAP, 100)], start, start)
    assert missing['data'][0]['value'] is None
    assert missing['skipped_incomplete_hours'] == 1


def test_count_hours_strict_boundaries():
    d = date(2026, 4, 2)
    rule = config(expression=f'IF({LOAD} >= {CAP}, 1, 0)',
                  unit='1', aggregation='SUM', hour_start=18, hour_end=20)
    samples = rows(d, 100, 99, 18) + rows(d, 100, 100, 19) + rows(d, 100, 101, 20)
    result = compute(rule, samples, d, d)['data'][0]
    assert result['value'] == 2  # equality and overload both match
    assert result['complete'] is True
    with pytest.raises(FormulaError):
        valid_definition(config(aggregation='SUM'), {CAP: 'kW', LOAD: 'kW'})
    with pytest.raises(FormulaError):
        valid_definition(config(hour_start=23, hour_end=2), {CAP: 'kW', LOAD: 'kW'})


def test_moving_average_uses_calendar_days_and_missing_data():
    start = date(2026, 4, 1)
    from datetime import timedelta
    samples = []
    for index in range(9):
        samples += rows(start + timedelta(days=index), 100, 90 - index)
    result = compute(config(mode='moving_avg', aggregation='AVG',
                            resolution='day', moving_days=3), samples,
                     start + timedelta(days=3), start + timedelta(days=8))
    assert len(result['data']) == 6
    assert result['data'][0]['value'] == 12  # 10,11,12 (calendar window)
    assert result['data'][0]['complete']
    removed = [row for row in samples if row[0] != start + timedelta(days=5)]
    bad = compute(config(mode='moving_avg', aggregation='AVG',
                         resolution='day', moving_days=3), removed,
                  start + timedelta(days=3), start + timedelta(days=8))
    assert bad['data'][2]['value'] is None
    assert bad['data'][3]['value'] is None
    assert bad['data'][4]['value'] is None
    assert bad['data'][5]['value'] == 17


def test_yoy_partial_and_zero_baseline_not_fake_growth():
    rule = config(expression=LOAD, mode='yoy', unit='kW', resolution='month', aggregation='MAX')
    source = rows(date(2025, 4, 1), 100, 0) + rows(date(2026, 4, 1), 100, 120)
    result = compute(rule, source, date(2026, 4, 1), date(2026, 4, 30))['data'][0]
    assert result['previous_value'] == 0
    assert result['value'] is None
    assert result['comparable'] is False
    source = rows(date(2025, 4, 1), 100, 100) + rows(date(2026, 4, 1), 100, 120)
    result = compute(rule, source, date(2026, 4, 1), date(2026, 4, 30))['data'][0]
    assert result['value'] == 20
    assert result['complete'] is False  # numeric is provisional


def test_reject_unsafe_and_large_ranges():
    units = {CAP: 'kW', LOAD: 'kW'}
    for expr in ('__import__("os")', f'{LOAD}.__class__', f'{LOAD}[0]'):
        with pytest.raises(FormulaError):
            valid_definition(config(expression=expr), units)
    with pytest.raises(FormulaError):
        validate_range(date(2020, 1, 1), date(2026, 1, 1), 'day')


def admin(client):
    login = client.post('/api/auth/login', json={
        'username': 'admin', 'password': os.environ['ADMIN_PASSWORD'],
    })
    assert login.status_code == 200, login.text
    return {'X-CSRF-Token': login.json()['csrf']}


def test_api_preview_create_run_privilege_and_no_mutation():
    with TestClient(app) as client:
        headers = admin(client)
        with SessionLocal() as db:
            mid = {m.code: m.id for m in db.query(Metric).filter(Metric.code.in_([CAP, LOAD]))}
            # Keep raw snapshots unchanged; route reads but never updates these rows.
            hr = HourRecord(day=date(2026, 7, 16), hour=18,
                            timestamp_utc=datetime(2026, 7, 16, 10, tzinfo=timezone.utc))
            db.add(hr); db.flush()
            db.add_all([Reading(hour_id=hr.id, metric_id=mid[CAP], value=50_000, source='import'),
                        Reading(hour_id=hr.id, metric_id=mid[LOAD], value=45_000, source='import')])
            db.commit()
            hour_id = hr.id
        definition = {
            'code': 'cadangan_ujicoba_historis', 'name': 'Cadangan Daya Uji',
            **config(),
        }
        payload = {**definition, 'start': '2026-07-16', 'end': '2026-07-16'}
        assert client.post('/api/historical-calculations/preview', json=payload).status_code == 403
        preview = client.post('/api/historical-calculations/preview', json=payload, headers=headers)
        assert preview.status_code == 200, preview.text
        assert preview.json()['data'][0]['value'] == 5000
        assert client.post('/api/historical-calculations', json=definition,
                           headers={'X-CSRF-Token': 'invalid'}).status_code == 403
        created = client.post('/api/historical-calculations', json=definition, headers=headers)
        assert created.status_code == 201, created.text
        assert client.post('/api/historical-calculations', json=definition, headers=headers).status_code == 409
        identifier = created.json()['id']
        result = client.get(f'/api/historical-calculations/{identifier}/run',
                            params={'start': '2026-07-16', 'end': '2026-07-16'})
        assert result.status_code == 200
        assert result.json()['data'][0]['count'] == 1
        assert client.get('/api/historical-calculations').json()[0]['name'] == 'Cadangan Daya Uji'
        with SessionLocal() as db:
            readings = db.query(Reading).filter_by(hour_id=hour_id).all()
            assert len(readings) == 2
            assert {float(r.value) for r in readings} == {50_000, 45_000}
        migration(engine); migration(engine)
        with SessionLocal() as db:
            assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
