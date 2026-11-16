"""V1.4.2.1/V1.4.3: isolated, authentic SQLite API + pure calculation regressions."""
import os
import tempfile
from decimal import Decimal
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_unit_visual_qa_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'QA-Strong-Admin-Password-2026'

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, Reading
from app.modules.units.migrations import run as migrate
from app.modules.units.service import UnitError, UnitSpec, convert
from app.modules.units.formula import validate_units, evaluate_units
from app.modules.formulas.engine import FormulaError, MissingValue
from app.modules.units.models import UnitDefinition
from app.db import engine


def login(client):
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200, r.text
    return {'X-CSRF-Token': r.json()['csrf']}


def test_units_dimensions_and_formula_conversion():
    units = {
        'kW': UnitSpec('kW', 'active_power', Decimal('1')),
        'MW': UnitSpec('MW', 'active_power', Decimal('1000')),
        'kVA': UnitSpec('kVA', 'apparent_power', Decimal('1')),
        '%': UnitSpec('%', 'ratio', Decimal('0.01')),
    }
    assert convert(50, units['MW'], units['kW']) == 50000
    assert convert(50000, units['kW'], units['MW']) == 50
    assert convert(50, units['%'], UnitSpec('1', 'ratio', Decimal('1'))) == .5
    try:
        convert(50000, units['kW'], units['kVA'])
        assert False, 'kW is not kVA'
    except UnitError:
        pass
    sources = {'cap': 'MW', 'load': 'kW'}
    validate_units('cap - load', 'MW', sources, units)
    assert evaluate_units('cap - load', {'cap': 50, 'load': 45000}, 'MW', sources, units) == 5
    assert evaluate_units('load / cap * 100', {'cap': 50, 'load': 45000}, '%', sources, units) == 90
    assert evaluate_units('IF(cap > 45, cap - load, 0)', {'cap': 50, 'load': 45000}, 'MW', sources, units) == 5
    assert evaluate_units('IF(cap > 50, cap - load, 0)', {'cap': 50, 'load': 45000}, 'MW', sources, units) == 0
    try:
        validate_units('cap + extra', 'MW', {**sources, 'extra': 'kVA'}, units)
        assert False, 'incompatible dimensions'
    except FormulaError:
        pass
    try:
        evaluate_units('cap - load', {'cap': 50}, 'MW', sources, units)
        assert False, 'missing value must not be zero'
    except MissingValue:
        pass


def test_master_units_custom_and_formula_api():
    with TestClient(app) as client:
        auth = login(client)
        before = client.get('/api/units').json()
        assert any(u['code'] == 'kW' and u['builtin'] for u in before)
        created = client.post('/api/units', headers=auth, json={
            'code': 'GW', 'name': 'Gigawatt', 'dimension': 'active_power', 'factor': 1000000})
        assert created.status_code == 201, created.text
        assert client.get('/api/units/convert', params={'value': 1, 'source': 'GW', 'target': 'MW'}).json()['result'] == 1000
        assert client.get('/api/units/convert', params={'value': 1, 'source': 'kW', 'target': 'kVA'}).status_code == 422
        assert client.post('/api/units', headers=auth, json={
            'code': 'GW', 'name': 'Duplicate', 'dimension': 'active_power', 'factor': 1000}).status_code == 409
        bad_unit = client.post('/api/metrics', headers=auth, json={
            'code': 'badunit', 'name': 'Invalid Unit', 'unit': 'ZZZ', 'group_name': 'REKAP'})
        assert bad_unit.status_code == 422
        custom = client.post('/api/metrics', headers=auth, json={
            'code': 'tes_cap_mw', 'name': 'Daya Uji MW', 'unit': 'MW', 'group_name': 'REKAP'})
        assert custom.status_code == 200, custom.text
        preview = client.post('/api/formulas/preview', headers=auth, json={
            'expression': 'tes_cap_mw - beban_sistem_kw', 'unit': 'MW',
            'samples': {'tes_cap_mw': 50, 'beban_sistem_kw': 45000}})
        assert preview.status_code == 200 and preview.json()['result'] == 5, preview.text
        created_formula = client.post('/api/formulas', headers=auth, json={
            'code': 'cadangan_mw_143', 'name': 'Cadangan MW', 'unit': 'MW',
            'group_name': 'REKAP', 'expression': 'tes_cap_mw - beban_sistem_kw'})
        assert created_formula.status_code == 201, created_formula.text
        with SessionLocal() as db:
            before_readings = db.query(Reading).count()
        migrate(engine); migrate(engine)
        with SessionLocal() as db:
            assert db.query(Reading).count() == before_readings
            assert db.query(UnitDefinition).filter_by(code='GW').count() == 1
        assert client.put('/api/units/MW/status', headers=auth, json={'active': False}).status_code == 409
        assert client.put('/api/units/GW/status', headers=auth, json={'active': False}).status_code == 200
        assert client.get('/api/units/convert', params={'value': 1, 'source': 'kW', 'target': 'MW'}).json()['result'] == .001


def test_visualization_panel_defaults_and_validation():
    with TestClient(app) as client:
        auth=login(client)
        panel={'id':'advanced-line','title':'Perbandingan Berau','kind':'step','source':'metric',
               'metric_codes':['daya_pasok_pembangkit_kw','beban_sistem_kw'],
               'source_id':None,'aggregation':'avg','w':12,'h':2,
               'legend':'right','decimals':3,'display_unit':'MW',
               'colors':{'daya_pasok_pembangkit_kw':'#123abc','beban_sistem_kw':'#fda021'},
               'show_points':True}
        def create(p):
            return client.post('/api/dashboard-builder',headers=auth,
                               json={'name':'Advanced QA Dashboard','scope':'personal','panels':[p]})
        good=create(panel)
        assert good.status_code==201, good.text
        assert good.json()['panels'][0]['display_unit']=='MW'
        assert good.json()['panels'][0]['legend']=='right'
        assert create({**panel,'display_unit':'kVA'}).status_code == 422
        assert create({**panel,'colors':{'beban_sistem_kw':'url(javascript:alert(1))'}}).status_code == 422
        assert create({**panel,'kind':'stacked_bar'}).status_code == 422
        assert create({**panel,'legend':'invalid'}).status_code == 422
        assert create({**panel,'decimals':7}).status_code == 422
        assert create({**panel,'display_unit':None,'colors':{}}).status_code == 201
        legacy={'id':'legacy','title':'Grafik Lama','kind':'line','source':'metric',
                'metric_codes':['beban_sistem_kw'],'source_id':None,'aggregation':'avg','w':6,'h':2}
        assert create(legacy).status_code == 201


def test_historical_and_engineering_reuse_unit_registry():
    with TestClient(app) as client:
        auth=login(client)
        metric=client.post('/api/metrics', headers=auth, json={
            'code':'source_mw_v143', 'name':'Daya Uji MW V143', 'unit':'MW',
            'group_name':'REKAP'})
        assert metric.status_code==200, metric.text
        settings={
            'code':'reserve_history_v143','name':'Cadangan Uji MW',
            'expression':'source_mw_v143 - beban_sistem_kw','unit':'MW',
            'aggregation':'AVG','resolution':'day','mode':'period',
            'moving_days':7,'hour_start':0,'hour_end':23}
        saved=client.post('/api/historical-calculations', headers=auth, json=settings)
        assert saved.status_code==201, saved.text
        preview=client.post('/api/historical-calculations/preview',headers=auth,
                            json={**settings,'start':'2026-11-01','end':'2026-11-02'})
        assert preview.status_code==200, preview.text
        rule={
            'code':'reserve_rule_v143','name':'Status Cadangan Uji MW',
            'expression':'source_mw_v143 - beban_sistem_kw', 'unit':'MW',
            'direction':'below','warning_threshold':10,'critical_threshold':5,
            'effective_from':'2026-11-01','reference_note':'Simulasi QA, bukan batas resmi PLN'}
        created=client.post('/api/engineering-rules', headers=auth, json=rule)
        assert created.status_code==201, created.text
        result=client.post('/api/engineering-rules/preview', headers=auth,
            json={**rule,'samples':{'source_mw_v143':50,'beban_sistem_kw':45000}})
        assert result.status_code==200, result.text
        assert result.json()['result']['value']==5
        assert result.json()['result']['status']=='critical'
