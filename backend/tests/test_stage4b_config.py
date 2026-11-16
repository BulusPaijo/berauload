"""Stage 4b tests are synthetic, use the temporary SQLite fixture from 4a."""
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from test_stage4a_units import site, login, as_unit
from app import main
from app.db import Asset, Metric, Reading, HourRecord, AuditLog
from app.modules.formulas.models import SchemaMigration
from app.modules.org_units.models import OrgUnit, UnitDayState
from app.modules.org_units.migration_config import CONFIG_TABLES, VERSION, backfill_once
from app.modules.topology.models import TopologyDiagram
from app.modules.input_forms.models import InputFormTab


def test_config_migration_one_time_and_restart_stability(site):
    admin, Session, head, ids = site
    with Session() as db:
        before = {table: db.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                  for table in (*CONFIG_TABLES, 'audit_logs', 'readings', 'hour_records','day_states')}
        for table in CONFIG_TABLES:
            assert db.execute(text(f'SELECT COUNT(*) FROM {table} WHERE unit_id IS NULL')).scalar() == 0, table
        assert db.execute(text('SELECT COUNT(*) FROM audit_logs WHERE unit_id IS NULL')).scalar() >= 0
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        table = db.query(TopologyDiagram).filter_by(unit_id=ids['home']).first()
    main.setup(); main.setup()
    with Session() as db:
        after = {table: db.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                 for table in before}
        assert before == after
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
    assert backfill_once(main.engine) is False


def test_topology_configuration_scoped_and_root_allowed(site):
    admin, Session, ah, ids = site
    layout = {'canvas':{'w':1600,'h':900,'grid':10},'symbols':[],'wires':[],'boxes':[], 'areas':[]}
    a=admin.post('/api/topology',headers=as_unit(ah,ids['other']),json={
        'name':'Diagram ULP Lain','layout':layout})
    assert a.status_code == 201,a.text
    b=admin.post('/api/topology',headers=as_unit(ah,ids['home']),json={
        'name':'Diagram ULP Tanjung','layout':layout})
    assert b.status_code == 201,b.text
    rid=admin.post('/api/topology',headers=as_unit(ah,ids['root']),json={
        'name':'Diagram UP3','layout':layout})
    assert rid.status_code == 201,rid.text
    for own, foreign in ((ids['other'],b.json()['id']),(ids['home'],a.json()['id'])):
        assert admin.get(f'/api/topology/{foreign}',headers=as_unit(ah,own)).status_code==404
    with TestClient(main.app) as operator:
        op=login(operator, 'operator_u')
        resp=operator.get('/api/topology',headers=as_unit(op,ids['other']))
        assert resp.status_code==200 and [r['id'] for r in resp.json()] == [a.json()['id']]
        assert operator.get(f'/api/topology/{b.json()["id"]}',
                            headers=as_unit(op,ids['other'])).status_code==404
        assert operator.post('/api/topology',headers=as_unit(op,ids['other']),json={
            'name':'Tidak sah','layout':layout}).status_code==403


def test_unit_form_defaults_and_root_rejection(site):
    admin, Session, ah, ids=site
    new=admin.post('/api/org-units', headers=ah, json={
        'code':'ulp_stage4b_new','name':'ULP QA 4b', 'level':'ulp','parent_id':ids['root']})
    assert new.status_code==201,new.text
    uid=new.json()['id']
    form=admin.get('/api/input-form/config',headers=as_unit(ah,uid))
    assert form.status_code==200,form.text
    assert len(form.json()['tabs'])==5 and form.json()['placements']==[]
    assert admin.put('/api/input-form/config',headers=as_unit(ah,ids['root']),json={
        'expected_version':1,'tabs':[{'code':'REKAP','name':'Rekap','active':True}],
        'placements':[]}).status_code==422
    with Session() as db:
        assert db.query(InputFormTab).filter_by(unit_id=uid).count()==5


def test_copy_settings_preview_commit_transaction_no_readings(site):
    admin, Session, ah, ids=site
    unit=admin.post('/api/org-units',headers=ah,json={
        'code':'ulp_stage4b_copy','name':'ULP Copy QA', 'level':'ulp','parent_id':ids['root']})
    assert unit.status_code==201,unit.text
    dest=unit.json()['id']
    body={'source_unit_id':ids['home'],'include_topology':False}
    url=f'/api/org-units/{dest}/copy-settings'
    plan=admin.post(url+'/preview',headers=ah,json=body)
    assert plan.status_code==200,plan.text
    assert plan.json()['assets']['pltu_lati']=='ulp_stage4b_copy_pltu_lati'
    assert plan.json()['metrics']['pltu_lati_cb33_kw']=='ulp_stage4b_copy_pltu_lati_cb33_kw'
    with Session() as db:
        before=(db.query(Reading).count(),db.query(HourRecord).count(),db.query(UnitDayState).count())
    action=admin.post(url+'/commit',headers=ah,json=body)
    assert action.status_code==200,action.text
    with Session() as db:
        assert (db.query(Reading).count(),db.query(HourRecord).count(),db.query(UnitDayState).count())==before
        assert db.query(Asset).filter_by(code='ulp_stage4b_copy_pltu_lati',unit_id=dest).first()
        assert db.query(Metric).filter_by(code='ulp_stage4b_copy_pltu_lati_cb33_kw',unit_id=dest).first()
        assert db.query(AuditLog).filter_by(action='org_settings_copy',unit_id=dest).count()==1
    again=admin.post(url+'/commit',headers=ah,json=body)
    assert again.status_code==409
    assert admin.post(url+'/preview',headers={'X-CSRF-Token':'wrong'},json=body).status_code==403


def test_reject_cross_unit_reference_without_leaking_details(site):
    admin, Session, ah, ids=site
    external=admin.post('/api/report-builder/preview', headers=as_unit(ah,ids['other']),json={
        'blocks':[{'id':'a','title':'Bad ref','kind':'stat',
                    'metric_codes':['pltu_lati_cb33_kw']}],
        'start':'2026-11-01','end':'2026-11-01'})
    assert external.status_code in (404,422),external.text
    assert admin.get('/api/report-builder',headers=as_unit(ah,ids['other'])).status_code==200
    assert admin.get('/api/data-export/templates',headers=as_unit(ah,ids['other'])).json()==[]
    assert admin.get('/api/historical-calculations',headers=as_unit(ah,ids['other'])).json()==[]
    assert admin.get('/api/engineering-rules',headers=as_unit(ah,ids['other'])).json()==[]


def test_copy_rolls_back_all_configuration_on_mid_transaction_failure(site, monkeypatch):
    import pytest
    from app.modules.org_units import copy_settings
    admin, Session, ah, ids=site
    new=admin.post('/api/org-units',headers=ah,json={
        'code':'ulp_stage4b_failed','name':'ULP Gagal QA', 'level':'ulp',
        'parent_id':ids['root']})
    assert new.status_code==201,new.text
    dest=new.json()['id']
    with Session() as db:
        src=db.get(OrgUnit, ids['home']);target=db.get(OrgUnit,dest)
        def fault(*args, **kwargs):
            raise RuntimeError('synthetic copy failure')
        monkeypatch.setattr(copy_settings, '_copy_tabs', fault)
        with pytest.raises(RuntimeError, match='synthetic'):
            copy_settings.commit(db, src, target, False, 1)
    with Session() as db:
        assert db.query(Asset).filter_by(unit_id=dest).count()==0
        assert db.query(Metric).filter_by(unit_id=dest).count()==0
        assert db.query(AuditLog).filter_by(action='org_settings_copy',unit_id=dest).count()==0
        assert db.query(InputFormTab).filter_by(unit_id=dest).count()==5  # defaults remain


def test_foreign_saved_configuration_ids_return_404(site):
    from app.modules.dashboard_builder.models import DashboardLayout
    from app.modules.historical.models import HistoricalDefinition
    from app.modules.engineering.models import EngineeringRule
    from app.modules.data_export.models import ExportTemplate
    from app.modules.report_builder.models import ReportTemplate
    admin, Session, ah, ids=site
    with Session() as db:
        dash=DashboardLayout(name='Home unit dashboard', scope='system', owner_id=0,
                             panels=[],unit_id=ids['home'])
        hist=HistoricalDefinition(code='qa_home_hist_4b',name='QA Hist',
            expression='pltu_lati_cb33_kw',unit='kW',aggregation='AVG',
            resolution='month',mode='period',unit_id=ids['home'])
        rule=EngineeringRule(code='qa_home_rule_4b',name='QA Rule',
            expression='pltu_lati_cb33_kw',unit='kW',direction='above',
            warning_threshold=1,critical_threshold=2,effective_from=date(2026,1,1),
            reference_note='Aturan sintetis untuk testing',status='active',unit_id=ids['home'])
        report=ReportTemplate(name='Home unit report',scope='system',owner_id=0,
                              blocks=[],unit_id=ids['home'])
        export=ExportTemplate(name='Home unit export',scope='system',owner_id=0,
                              spec={},unit_id=ids['home'])
        db.add_all((dash,hist,rule,report,export));db.commit()
        identifiers=(dash.id,hist.id,rule.id,report.id,export.id)
    d,h,r,p,e=identifiers
    urls=(f'/api/dashboard-builder/{d}',f'/api/historical-calculations/{h}/revisions',
          f'/api/engineering-rules/{r}/revisions',
          f'/api/report-builder/{p}/download?start=2026-11-01&end=2026-11-01',
          f'/api/data-export/templates/{e}/archive')
    for url in urls:
        if 'archive' in url:
            resp=admin.post(url,headers=as_unit(ah,ids['other']))
        else:
            resp=admin.get(url,headers=as_unit(ah,ids['other']))
        assert resp.status_code==404, (url,resp.status_code,resp.text)


def test_root_accepts_dashboard_but_rejects_input_configuration(site):
    admin, Session, ah, ids=site
    root_header=as_unit(ah,ids['root'])
    result=admin.post('/api/dashboard-builder',headers=root_header,json={
        'name':'UP3 Recap Dashboard','scope':'system','panels':[]})
    assert result.status_code==201,result.text
    assert admin.get('/api/dashboard-builder',headers=root_header).status_code==200
    assert admin.get('/api/input-form/config',headers=root_header).json()['tabs']==[]
    assert admin.put('/api/input-form/config',headers=root_header,json={
        'expected_version':1,'tabs':[{'code':'INPUT','name':'Input','active':True}],
        'placements':[]}).status_code==422


def test_stage4a_sqlite_schema_migrates_without_audit_backfill(tmp_path):
    """Simulate real pre-4b SQLite tables lacking unit_id, not Base.create_all."""
    from sqlalchemy import create_engine, inspect
    from app.modules.org_units.migration_config import ensure_schema, backfill_once
    from app.modules.org_units.models import OrgUnit
    engine=create_engine('sqlite:///'+str(tmp_path/'old.db'))
    with engine.begin() as conn:
        OrgUnit.__table__.create(conn)
        conn.execute(OrgUnit.__table__.insert(), [
            {'id':1,'code':'up3_berau','name':'UP3 Berau','level':'up3',
             'parent_id':None,'legacy_home':False},
            {'id':2,'code':'ulp_tanjung_redeb','name':'ULP Tanjung Redeb',
             'level':'ulp','parent_id':1,'legacy_home':True}])
        conn.execute(text('CREATE TABLE input_form_tabs ('
                          'id INTEGER PRIMARY KEY, code VARCHAR(40), name VARCHAR(100), '
                          'display_order INTEGER, active BOOLEAN)'))
        conn.execute(text("INSERT INTO input_form_tabs VALUES (1,'PEMBANGKIT','Pembangkit',0,1)"))
        conn.execute(text('CREATE TABLE audit_logs ('
                          'id INTEGER PRIMARY KEY, action VARCHAR(90))'))
        conn.execute(text("INSERT INTO audit_logs VALUES (1,'legacy_log')"))
    ensure_schema(engine)
    assert backfill_once(engine) is True
    assert backfill_once(engine) is False
    ensure_schema(engine)
    with engine.begin() as conn:
        assert 'unit_id' in {c['name'] for c in inspect(conn).get_columns('input_form_tabs')}
        assert conn.execute(text('SELECT unit_id FROM input_form_tabs')).scalar_one()==2
        assert conn.execute(text('SELECT unit_id FROM audit_logs')).scalar_one() is None
        assert conn.execute(text('SELECT COUNT(*) FROM input_form_tabs')).scalar_one()==1
    engine.dispose()


def test_personal_config_owner_resolves_only_unambiguous_unit(site):
    """Migrate personal configuration to its sole working ULP, else legacy_home."""
    from app.db import User
    from app.modules.report_builder.models import ReportTemplate
    admin, Session, _headers, ids = site
    with Session() as db:
        other_user = db.query(User).filter_by(username='operator_u').one()
        root_user = db.query(User).filter_by(username='management_root').one()
        one = ReportTemplate(name='Personal ULP unik', scope='personal',
                             owner_id=other_user.id, blocks=[], unit_id=None)
        fallback = ReportTemplate(name='Personal UP3 ambigu', scope='personal',
                                  owner_id=root_user.id, blocks=[], unit_id=None)
        db.add_all((one, fallback))
        db.query(SchemaMigration).filter_by(version=VERSION).delete()
        db.commit()
        row_ids = (one.id, fallback.id)
    assert backfill_once(main.engine) is True
    with Session() as db:
        assert db.get(ReportTemplate, row_ids[0]).unit_id == ids['other']
        assert db.get(ReportTemplate, row_ids[1]).unit_id == ids['home']
    main.setup()
    with Session() as db:
        assert db.get(ReportTemplate, row_ids[0]).unit_id == ids['other']
        assert db.get(ReportTemplate, row_ids[1]).unit_id == ids['home']
