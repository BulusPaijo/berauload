"""V1.1 unit/integration tests; independent ephemeral SQLite, no production DB."""
import os
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_formula_qa_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Formula-Password-123456789'

from fastapi.testclient import TestClient
from app.main import app
from app.modules.formulas.engine import evaluate, validate, FormulaError, MissingValue


def test_calculation_boundaries_and_missing_values():
    units = {'load_kw': 'kW', 'capacity_kw': 'kW', 'frequency_hz': 'Hz'}
    assert validate('load_kw / capacity_kw * 100', '%', units)
    assert evaluate('load_kw / capacity_kw * 100', {'load_kw': 101, 'capacity_kw': 100}) == 101
    assert evaluate('load_kw / capacity_kw * 100', {'load_kw': 0, 'capacity_kw': 100}) == 0
    assert evaluate('IF(load_kw >= capacity_kw, 1, 0)', {'load_kw': 100, 'capacity_kw': 100}) == 1
    assert evaluate('SUM(load_kw, capacity_kw)', {'load_kw': 0, 'capacity_kw': 100}) == 100
    assert evaluate('AVG(load_kw, capacity_kw)', {'load_kw': 4, 'capacity_kw': 6}) == 5
    assert evaluate('MIN(load_kw, capacity_kw)', {'load_kw': 4, 'capacity_kw': 6}) == 4
    assert evaluate('MAX(load_kw, capacity_kw)', {'load_kw': 4, 'capacity_kw': 6}) == 6
    for expression in ('load_kw / 0', 'load_kw / (capacity_kw - capacity_kw)'):
        try:
            evaluate(expression, {'load_kw': 5, 'capacity_kw': 5})
            assert False, 'Division-by-zero must fail'
        except FormulaError:
            pass
    try:
        evaluate('load_kw + capacity_kw', {'load_kw': 20})
        assert False, 'Missing measurement must fail'
    except MissingValue as exc:
        assert 'capacity_kw' in exc.names


def test_reject_unsafe_and_mismatched_units():
    for expression in ('__import__("os")', 'load_kw.__class__', 'load_kw[0]',
                       '(x for x in (1,2))', 'load_kw ** 2', 'load_kw + "a"'):
        try:
            validate(expression, 'kW', {'load_kw': 'kW'})
            assert False, expression
        except FormulaError:
            pass
    try:
        validate('SUM(load_kw, frequency_hz)', 'kW', {'load_kw': 'kW', 'frequency_hz': 'Hz'})
        assert False, 'mixed units must fail'
    except FormulaError:
        pass


def test_formula_crud_preview_hourly_and_chart_preserve_old():
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
        assert login.status_code == 200
        headers = {'X-CSRF-Token': login.json()['csrf']}
        catalog = client.get('/api/catalog').json()
        assert any(m['code'] == 'daya_mampu_sistem_kw' and m['mode'] == 'input' for m in catalog['metrics'])
        assert next(m for m in catalog['metrics'] if m['code'] == 'daya_pasok_pembangkit_kw')['name'] == 'Daya Mampu Sistem (kolom H rekap)'
        assert 'Legacy' in next(m for m in catalog['metrics'] if m['code'] == 'daya_mampu_sistem_kw')['name']
        formula = {
            'code': 'cadangan_daya_kw', 'name': 'Cadangan Daya', 'unit': 'kW',
            'group_name': 'REKAP', 'expression': 'daya_mampu_sistem_kw - beban_sistem_kw',
        }
        response = client.post('/api/formulas', json=formula, headers=headers)
        assert response.status_code == 201, response.text
        assert client.post('/api/formulas', json=formula, headers=headers).status_code == 422
        bad = {**formula, 'code': 'salah_satuan_kw', 'expression': 'frequency_hz + beban_sistem_kw'}
        assert client.post('/api/formulas', json=bad, headers=headers).status_code == 422
        sample = client.post('/api/formulas/preview', headers=headers,
                             json={'expression': formula['expression'], 'unit': 'kW',
                                   'samples': {'beban_sistem_kw': 48000, 'daya_mampu_sistem_kw': 60000}})
        assert sample.status_code == 200 and sample.json()['result'] == 12000
        assert client.post('/api/formulas/preview', headers=headers,
                           json={'expression': formula['expression'], 'unit': 'kW', 'samples': {}}).json()['result'] is None

        # V1 formula must still be exactly the same as before upgrade.
        source = {'pltu_lati_cb33_kw': 2938, 'pltu_lati_cb31_kw': 4602,
                  'sewa_tama_1_kw': 5000, 'sewa_tama_2_kw': 5000, 'pltd_kw': 2400,
                  'pltu_berau_og3_kw': 4924, 'pltu_berau_og4_kw': 1366,
                  'pltd_berau_kw': 725, 'beban_suaran_kw': 1714.18,
                  'incoming_gi_kw': 7870, 'daya_mampu_sistem_kw': 60000}
        put = client.put('/api/records/2026-11-03/19', json={'values': source}, headers=headers)
        assert put.status_code == 200, put.text
        assert put.json()['computed']['beban_sistem_kw'] == 35814.18
        assert put.json()['computed']['cadangan_daya_kw'] == 24185.82
        records = client.get('/api/records/day?day=2026-11-03').json()['hours'][19]['values']
        assert records['daya_mampu_sistem_kw'] == 60000
        assert records['cadangan_daya_kw'] == 24185.82
        chart = client.get('/api/monitoring/capacity-vs-load?start=2026-11-03&end=2026-11-03&granularity=hour')
        assert chart.status_code == 200, chart.text
        assert chart.json()['data'][0]['paired_hours'] == 1
        # Chart uses the actual Excel recap H (= daya_pasok_pembangkit_kw), never the V1.1 duplicate input.
        assert chart.json()['data'][0]['capacity_kw'] == 27944.18
        assert chart.json()['data'][0]['load_kw'] == 35814.18
        assert client.post('/api/days/2026-11-03/verify', json={'reason': 'Cek rumus'}, headers=headers).status_code == 200
        assert client.post('/api/days/2026-11-03/finalize', json={'reason': 'Final'}, headers=headers).status_code == 200
        assert client.put('/api/records/2026-11-03/19', json={'values': {'daya_mampu_sistem_kw': 10}}, headers=headers).status_code == 409


def test_chart_uses_existing_recap_h_calculation():
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
        h = {'X-CSRF-Token': login.json()['csrf']}
        source = {'pltu_lati_cb33_kw': 100, 'pltu_lati_cb31_kw': 100,
                  'sewa_tama_1_kw': 100, 'sewa_tama_2_kw': 100,
                  'pltd_kw': 100, 'pltu_berau_og3_kw': 100,
                  'pltu_berau_og4_kw': 100, 'pltd_berau_kw': 0,
                  'beban_suaran_kw': 0, 'incoming_gi_kw': 0}
        assert client.put('/api/records/2026-11-04/08', json={'values': source}, headers=h).status_code == 200
        body = client.get('/api/monitoring/capacity-vs-load?start=2026-11-04&end=2026-11-04&granularity=hour').json()['data'][0]
        assert body['load_hours'] == 1 and body['paired_hours'] == 1
        assert body['capacity_kw'] == 700 and body['load_kw'] == 700


def test_chart_reads_imported_excel_recap_h_without_duplicate_input():
    from io import BytesIO
    from openpyxl import Workbook
    book = Workbook()
    ws = book.active
    ws.title = '1'
    ws['B9'] = 1000  # Real source reading marks this hour as observed.
    ws['H36'] = 42000  # Source of truth: daya mampu sistem, recap column H.
    ws['J36'] = 36000  # Beban sistem, recap column J.
    payload = BytesIO()
    book.save(payload)
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={
            'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
        headers = {'X-CSRF-Token': login.json()['csrf']}
        preview = client.post('/api/imports/preview', data={
            'year': '2026', 'month': '12'}, files={
            'file': ('test_h.xlsx', payload.getvalue(),
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            headers=headers)
        assert preview.status_code == 200, preview.text
        assert preview.json()['sample'][0]['values']['daya_pasok_pembangkit_kw'] == 42000
        commit = client.post('/api/imports/commit', json={
            'token': preview.json()['token']}, headers=headers)
        assert commit.status_code == 200, commit.text
        response = client.get('/api/monitoring/capacity-vs-load', params={
            'start': '2026-12-01', 'end': '2026-12-01', 'granularity': 'hour'})
        assert response.status_code == 200
        row = response.json()['data'][0]
        assert row['capacity_kw'] == 42000
        assert row['load_kw'] == 36000
        assert row['paired_hours'] == 1
        day = client.get('/api/records/day?day=2026-12-01').json()['hours'][0]['values']
        assert 'daya_mampu_sistem_kw' not in day
