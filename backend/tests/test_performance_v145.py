"""New read path must match old analytics, and cache must never stay stale."""
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
root = Path(tempfile.mkdtemp(prefix='berauload_v145_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'test.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'V145-Admin-Test-Passphrase-2026'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, HourRecord, Reading, Metric
from app.modules.performance.cache import clear_reading_cache, get_or_compute

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client):
    response = client.post('/api/auth/login', json={
        'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


def seed():
    with SessionLocal() as db:
        codes = {m.code: m.id for m in db.query(Metric).filter(Metric.code.in_([CAP, LOAD]))}
        for hour, cap, load in [(0, 50000, 0), (1, 52000, None), (2, 51000, 48000)]:
            entry = HourRecord(day=date(2031, 8, 8), hour=hour,
                timestamp_utc=datetime(2031, 8, 7, 16 + hour, tzinfo=timezone.utc))
            db.add(entry); db.flush()
            for code, value in [(CAP, cap), (LOAD, load)]:
                if value is not None:
                    db.add(Reading(hour_id=entry.id, metric_id=codes[code],
                                   value=Decimal(value), source='test'))
        db.commit()
    clear_reading_cache()


def test_batched_vs_legacy_and_protected():
    with TestClient(app) as client:
        login(client); seed()
        args = '?start=2031-08-08&end=2031-08-08&granularity=hour'
        batched = client.get('/api/performance/series' + args + f'&codes={CAP},{LOAD}')
        assert batched.status_code == 200, batched.text
        data = batched.json()['data']
        for code in (CAP, LOAD):
            legacy = client.get('/api/analytics' + args + '&metric=' + code)
            assert legacy.status_code == 200
            assert data[code] == legacy.json()['data']
        assert data[LOAD][0]['avg'] == 0
        assert len(data[LOAD]) == 2  # missing hour is not fabricated as zero
        assert client.get('/api/performance/series' + args + '&codes=missing').status_code == 404
        assert client.get('/api/performance/series' + args + '&codes=' + CAP + ',' + CAP).status_code == 422
        assert client.get('/api/performance/series' + args.replace('hour', 'bogus') + '&codes=' + CAP).status_code == 422
        with TestClient(app) as guest:
            assert guest.get('/api/performance/series' + args + '&codes=' + CAP).status_code == 401


def test_cache_invalidated_on_real_record_write():
    input_code = 'pltu_lati_cb33_kw'
    day = '2031-08-09'
    with TestClient(app) as client:
        headers = login(client)
        path = (f'/api/performance/series?start={day}&end={day}'
                f'&granularity=hour&codes={input_code}')
        original = client.get(path).json()['data'][input_code]
        assert original == []
        saved = client.put(f'/api/records/{day}/0', headers=headers,
                           json={'values': {input_code: 12345}})
        assert saved.status_code == 200, saved.text
        fresh = client.get(path).json()['data'][input_code]
        assert fresh[0]['avg'] == 12345
        assert client.get('/api/analytics?start=' + day + '&end=' + day +
                          '&granularity=hour&metric=' + input_code).json()['data'] == fresh


def test_cache_generation_prevents_inflight_reinsertion():
    clear_reading_cache()
    calls=[]
    def compute():
        calls.append(1)
        clear_reading_cache()
        return {'value': 1}
    assert get_or_compute(('test', 1), compute) == {'value': 1}
    assert get_or_compute(('test', 1), lambda: {'value': 2}) == {'value': 2}
    assert len(calls) == 1
