"""Stage 9b: synthetic SQLite, no production fixtures and no changed legacy assertions."""
from copy import deepcopy
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import func
import pytest

from app import main
from app.db import AuditLog, HourRecord, Reading
from app.modules.substations.calculation_migrations import run, VERSION
from app.modules.substations.calculation_service import get_results
from app.modules.substations.models import SubstationMeasurement, SubstationValue
from app.modules.substations.models_calc import (GarduCalcColumn, GarduCalcRule,
    GarduCalcSettings, GarduCalcMark, GarduCalcValue, GarduCalcHistory)
from app.modules.formulas.models import SchemaMigration
from app.modules.formulas.engine import parse_formula, evaluate, evaluate_gardu, FormulaError
from test_stage4a_units import site, as_unit, login
from test_stage9a_substations import master, visit

BASE = '/api/substations/calculations'


def test_parser_secure_and_legacy_unchanged():
    assert evaluate('IF(a > 0, a * 2, 4)', {'a': 3}) == 6
    assert evaluate_gardu('IF(fase = 3, kva, 1/0)', {'fase': 3, 'kva': 200}, {}, {})[0] == 200
    assert evaluate_gardu('IF(fase = 1, 1/0, kva)', {'fase': 3, 'kva': 200}, {}, {})[0] == 200
    assert evaluate_gardu('1/kva', {'kva': 0}, {}, {})[0] is None
    assert evaluate_gardu('SUM_JURUSAN(i_r)', {}, {'i_r': [0, None]}, {}, skip_missing=True)[0] == 0
    assert evaluate_gardu('SUM_JURUSAN(i_r)', {}, {'i_r': [0, None]}, {}, skip_missing=False)[0] is None
    assert evaluate_gardu('SUM_JURUSAN(i_r)', {}, {'i_r': []}, {}, skip_missing=True)[0] is None
    for unsafe in ('__import__(1)', 'kva.__class__', 'kva[0]', '(lambda:3)()',
                   '[kva for _ in (1,)]', '"secret"', 'OPEN(1)', 'kva'+'+1'*150,
                   'ABS('*22+'kva'+')'*22):
        with pytest.raises(FormulaError):
            parse_formula(unsafe, frozenset({'SUM_JURUSAN'}))


def test_seed_idempotent_and_immutable_source(site):
    client,Session,admin,ids = site
    with Session() as db:
        assert db.query(GarduCalcColumn).count() == 13
        assert db.query(GarduCalcRule).count() == 11
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        row = db.query(GarduCalcColumn).filter_by(code='arus_nominal').one()
        row.name = 'Arus Nominal Disunting QA'
        db.commit()
    run(Session.kw['bind'])
    run(Session.kw['bind'])
    with Session() as db:
        assert db.query(GarduCalcColumn).count() == 13
        assert db.query(GarduCalcColumn).filter_by(code='arus_nominal').one().name == 'Arus Nominal Disunting QA'


def test_save_derived_flags_null_and_versions(site):
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']);_,g=master(client,h)
    with Session() as db:
        before=(db.query(HourRecord).count(),db.query(Reading).count())
    body=visit(g,values=[{'code':'I_R','line_no':1,'value':0},
        {'code':'I_R','line_no':2,'flag':'PUTUS'},
        {'code':'GROUND_TR','line_no':0,'flag':'PUTUS'}])
    saved=client.put('/api/substations/measurements',headers=h,json=body)
    assert saved.status_code==200,saved.text
    visit_id=saved.json()['id'];computed=saved.json()['calculated']
    assert computed['version']==1 and not computed['stale']
    cols={c['code']:c for c in computed['columns']}
    assert cols['total_r']['value'] is None
    assert cols['total_r']['incomplete']
    assert cols['total_r']['filled']==1 and cols['total_r']['total']==2
    assert cols['arus_nominal']['value']==pytest.approx(100000/(1.732*400),rel=1e-4)
    assert 'grounding' in {x['code'] for x in computed['matches']}
    with Session() as db:
        assert db.query(GarduCalcMark).filter_by(measurement_id=visit_id).one().version==1
        assert before==(db.query(HourRecord).count(),db.query(Reading).count())
    assert client.get(f'{BASE}/measurements/{visit_id}/results',headers=h).status_code==200


def test_admin_csrf_code_graph_preview_and_resume(site):
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']);_,g=master(client,h)
    saved=client.put('/api/substations/measurements',headers=h,json=visit(g,values=[
        {'code':'I_R','line_no':1,'value':40}, {'code':'I_R','line_no':2,'value':30},
        {'code':'I_S','line_no':1,'value':45}, {'code':'I_S','line_no':2,'value':25},
        {'code':'I_T','line_no':1,'value':50}, {'code':'I_T','line_no':2,'value':20}]))
    mid=saved.json()['id']
    with TestClient(main.app) as management:
        readonly=login(management,'management_root')
        assert management.get(BASE+'/definitions',headers=as_unit(readonly,ids['root'])).status_code==200
        assert management.post(BASE+'/column',headers=as_unit(readonly,ids['root']),
                               json={'code':'forbidden'}).status_code==403
    assert client.post(BASE+'/check',headers=h,json={'expression':'SUM_JURUSAN(i_r)','kind':'column'}).status_code==200
    assert client.post(BASE+'/check',headers=h,json={'expression':'__import__(1)'}).status_code==422
    check=client.post(BASE+'/check',headers=h,json={'expression':'unknown_gardu * 2'})
    assert check.status_code==422 and 'unknown_gardu' in check.text
    create={'code':'test_calc','name':'Test Hitung','unit':'A','decimals':1,
            'expression':'total_r * 2','empty_mode':'batal'}
    assert client.post(BASE+'/column',json=create).status_code==403  # missing CSRF
    created=client.post(BASE+'/column',headers=h,json=create)
    assert created.status_code==200,created.text
    cid=created.json()['id']
    assert client.patch(f'{BASE}/column/{cid}',headers=h,json={'code':'changed'}).status_code==409
    assert client.patch(f'{BASE}/column/{cid}',headers=h,json={'expression':'test_calc + 1'}).status_code==422
    assert client.patch(f'{BASE}/column/{cid}',headers=h,json={'expression':'total_r + nope'}).status_code==422
    test=client.post(BASE+'/test',headers=h,json={'measurement_id':mid,
         'code':'test_calc','expression':'total_r * 3'})
    assert test.status_code==200,test.text
    assert test.json()['draft']==210
    preview=client.post(BASE+'/preview',headers=h,json={'code':'test_calc',
         'expression':'total_r * 3'})
    assert preview.status_code==200,preview.text
    with Session() as db:
        assert db.get(GarduCalcMark,mid).version==1
        assert db.query(GarduCalcHistory).count()==1
    version=client.get(BASE+'/recalculate/status',headers=h).json()['version']
    assert version==2
    done=client.post(BASE+'/recalculate?limit=1',headers=h)
    assert done.status_code==200,done.text
    assert done.json()['remaining']==0
    repeat=client.post(BASE+'/recalculate?limit=1',headers=h)
    assert repeat.json()['processed']==0
    with Session() as db:
        assert db.get(GarduCalcMark,mid).version==2
        assert db.query(GarduCalcValue).filter_by(measurement_id=mid).count()==14
        assert db.query(SubstationMeasurement).filter_by(id=mid).one().revision==1
        assert db.query(AuditLog).filter_by(action='gardu_calc_column_save').count()==1
    assert client.patch(f'{BASE}/column/{cid}',headers=h,json={'active':False}).status_code==200


def test_category_bounds_and_multi_findings(site):
    client,Session,admin,ids=site
    h=as_unit(admin,ids['kp']);_,g=master(client,h)
    from app.modules.substations.calculation_service import compute
    with Session() as db:
        m=SubstationMeasurement(unit_id=ids['kp'],substation_id=g,measured_on=date(2034,2,2),
            session='MALAM',snapshot_power_kva=100,snapshot_phase=3,snapshot_line_count=1)
        db.add(m);db.flush()
        from app.modules.substations.models import SubstationParam
        for code,val in [('I_R',90),('I_S',90),('I_T',90),('I_N',95),
                         ('V_R0',220),('V_S0',219),('V_T0',221),
                         ('V_END_RN',190),('V_END_SN',192),('V_END_TN',194)]:
            param=db.query(SubstationParam).filter_by(code=code).one()
            db.add(SubstationValue(measurement_id=m.id,param_id=param.id,
                line_no=1 if param.scope=='line' else 0,value=val))
        db.flush()
        result=compute(db,m)
        assert len([r for r in result['matches'] if r['kind']=='category'])==1
        assert {'netral_tinggi','tegangan_drop','jatuh_tegangan_tinggi'} <= {
            r['code'] for r in result['matches']}
    # Equality thresholds are evaluated as conditions without rounding the input.
    from app.modules.formulas.engine import evaluate_gardu
    expressions=['x < 60','AND(x >= 60, x < 80)',
                 'AND(x >= 80, x <= 100)','x > 100']
    for value,category in [(59.999,0),(60,1),(80,2),(100,2),(100.001,3)]:
        matched=[i for i,e in enumerate(expressions) if evaluate_gardu(e,{'x':value},{},{})[0]]
        assert matched==[category]
