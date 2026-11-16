"""Stage 5 cross-unit source tests on synthetic SQLite, never production data."""
from datetime import date
from fastapi.testclient import TestClient
from test_stage4a_units import site, login, as_unit
from app import main
from app.db import Reading, Metric, HourRecord
from app.modules.unit_references.models import UnitSourceChange
from app.modules.formulas.models import SchemaMigration
from app.modules.unit_references.migrations import VERSION


def formula(client, head, owner, code, expression):
    return client.post('/api/formulas', headers=as_unit(head, owner), json={
        'code': code, 'name': code, 'unit': 'kW', 'group_name': 'REKAP',
        'expression': expression})


def write(client, head, unit, day, value):
    return client.put(f'/api/records/{day}/0', headers=as_unit(head, unit),
                      json={'values': value})


def reading(Session, code, day):
    with Session() as db:
        result = db.query(Reading.value).join(Metric, Reading.metric_id == Metric.id).join(
            HourRecord, Reading.hour_id == HourRecord.id).filter(
            Metric.code == code, HourRecord.day == date.fromisoformat(day),
            HourRecord.hour == 0).first()
        return float(result[0]) if result else None


def test_parent_references_and_complete_and_zero(site):
    admin, Session, ah, ids = site
    created = formula(admin, ah, ids['other'], 'other_combined_kw', 'SUM(other_load, kp_load)')
    assert created.status_code == 201, created.text
    root = formula(admin, ah, ids['root'], 'up3_explicit_kw', 'SUM(other_combined_kw, kp_load)')
    assert root.status_code == 201, root.text
    day = '2026-11-09'
    assert write(admin, ah, ids['kp'], day, {'kp_load': 7}).status_code == 200
    assert reading(Session, 'other_combined_kw', day) is None
    partial = admin.get(f'/api/formulas/completeness?day={day}&hour=0',
                        headers=as_unit(ah, ids['other']))
    assert partial.status_code == 200
    assert partial.json()['formulas'][0]['label'] == '1 dari 2 sumber terisi'
    # No partial aggregation. Zero is a real operand.
    assert write(admin, ah, ids['other'], day, {'other_load': 0}).status_code == 200
    assert reading(Session, 'other_combined_kw', day) == 7
    assert reading(Session, 'up3_explicit_kw', day) == 14
    stats = admin.get(f'/api/formulas/completeness?day={day}&hour=0',
                      headers=as_unit(ah, ids['other']))
    assert stats.status_code == 200, stats.text
    assert stats.json()['formulas'][0]['label'] == '2 dari 2 sumber terisi'
    assert write(admin, ah, ids['kp'], day, {'kp_load': 9}).status_code == 200
    assert reading(Session, 'other_combined_kw', day) == 9
    assert reading(Session, 'up3_explicit_kw', day) == 18
    status = admin.get(f'/api/unit-references/status?day={day}&codes=up3_explicit_kw',
                       headers=as_unit(ah, ids['root']))
    assert status.status_code == 200, status.text
    assert {u['unit_id'] for u in status.json()['units']} == {ids['other'], ids['kp']}


def test_locked_parent_stays_unchanged_and_root_follows_direct_source(site):
    admin, Session, ah, ids = site
    day = '2026-11-10'
    assert formula(admin, ah, ids['other'], 'frozen_ulp_kw', 'SUM(other_load, kp_load)').status_code == 201
    assert formula(admin, ah, ids['root'], 'live_up3_kw', 'SUM(frozen_ulp_kw, kp_load)').status_code == 201
    assert write(admin, ah, ids['kp'], day, {'kp_load': 10}).status_code == 200
    assert write(admin, ah, ids['other'], day, {'other_load': 5}).status_code == 200
    assert reading(Session, 'frozen_ulp_kw', day) == 15
    assert admin.post(f'/api/days/{day}/verify',headers=as_unit(ah, ids['other']),
                      json={'reason':'Tes status parent'}).status_code == 200
    missing_confirm = admin.post(f'/api/days/{day}/finalize',headers=as_unit(ah, ids['other']),
                      json={'reason':'Tes final parent'})
    assert missing_confirm.status_code == 409
    assert admin.post(f'/api/days/{day}/finalize',headers=as_unit(ah, ids['other']),
                      json={'reason':'Tes final parent', 'confirm_draft_sources':True}).status_code == 200
    assert write(admin, ah, ids['kp'], day, {'kp_load': 12}).status_code == 200
    assert reading(Session, 'frozen_ulp_kw', day) == 15
    assert reading(Session, 'live_up3_kw', day) == 27
    st = admin.get(f'/api/days/{day}/status', headers=as_unit(ah, ids['other']))
    assert st.json()['source_changed_after_final'] is True
    with Session() as db:
        assert db.query(UnitSourceChange).filter_by(unit_id=ids['other']).count() == 1
    assert admin.post(f'/api/days/{day}/reopen',headers=as_unit(ah, ids['other']),
                      json={'reason':'Koreksi sumber'}).status_code == 200
    assert reading(Session, 'frozen_ulp_kw', day) == 17
    assert reading(Session, 'live_up3_kw', day) == 29


def test_sibling_and_parent_protection_all_shared_refs(site):
    admin, _, ah, ids = site
    # Peer KP from a different ULP is forbidden; ancestor from KP is forbidden.
    assert formula(admin, ah, ids['other'], 'peer_bad_kw', 'foreign_kp_load + 1').status_code == 404
    assert formula(admin, ah, ids['kp'], 'above_bad_kw', 'other_load + 1').status_code == 404
    assert admin.get('/api/performance/series?start=2026-11-09&end=2026-11-09&codes=foreign_kp_load',
                     headers=as_unit(ah, ids['other'])).status_code == 404
    assert admin.post('/api/report-builder/preview', headers=as_unit(ah, ids['other']),json={
        'blocks':[{'id':'bad','kind':'stat','title':'Sibling', 'metric_codes':['foreign_kp_load']}],
        'start':'2026-11-09','end':'2026-11-09'}).status_code in (404,422)
    with TestClient(main.app) as kp:
        heads = login(kp, 'operator_kp')
        visible = kp.get('/api/unit-references/metrics', headers=as_unit(heads, ids['kp']))
        assert visible.status_code == 200
        assert {v['code'] for v in visible.json()['metrics']} == {'kp_load'}
        assert kp.get('/api/unit-references/metrics', headers=as_unit(heads, ids['other'])).status_code == 404
        assert kp.get('/api/unit-references/status?day=2026-11-09&codes=other_load',
                      headers=as_unit(heads, ids['kp'])).status_code == 404


def test_schema_startup_is_idempotent(site):
    _, Session, _, _ = site
    with Session() as db:
        before = db.query(UnitSourceChange).count()
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
    main.setup(); main.setup()
    with Session() as db:
        assert db.query(UnitSourceChange).count() == before
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1


def test_cross_unit_pickers_and_configuration_validation(site):
    admin, _, head, units = site
    ulp = as_unit(head, units['other'])
    kp = as_unit(head, units['kp'])
    picker = admin.get('/api/unit-references/metrics', headers=ulp)
    assert picker.status_code == 200
    listed = {row['code']: row for row in picker.json()['metrics']}
    assert 'kp_load' in listed and listed['kp_load']['source'] is True
    assert 'other_load' in listed and listed['other_load']['source'] is False
    assert listed['kp_load']['label'].endswith(' - '+listed['kp_load']['name'])
    for current, forbidden in ((ulp, 'foreign_kp_load'), (kp, 'other_load')):
        hist = dict(code='test_bad_hist', name='Tes formula lintas unit',
                    expression=forbidden, unit='kW', aggregation='AVG',
                    resolution='day', mode='period', moving_days=7,
                    hour_start=0, hour_end=23,
                    start='2026-11-09', end='2026-11-09')
        assert admin.post('/api/historical-calculations/preview', headers=current,
                          json=hist).status_code in (404, 422)
        rule = dict(code='test_bad_rule', name='Tes Rule Lintas Unit',
                    expression=forbidden, unit='kW', direction='above',
                    warning_threshold=10, critical_threshold=20,
                    reference_note='Aturan sintetis untuk testing',
                    effective_from='2026-11-09', samples={forbidden:2})
        assert admin.post('/api/engineering-rules/preview', headers=current,
                          json=rule).status_code in (404,422)
        exp = {'start':'2026-11-09', 'end':'2026-11-09',
               'columns':['tanggal',forbidden], 'granularity':'hour',
               'aggregation':'avg', 'format':'csv', 'headers':{},
               'unit_overrides':{}}
        assert admin.post('/api/data-export/preview', headers=current,
                          json=exp).status_code in (404,422)
        dash = {'name':'Dashboard QA Stage 5', 'scope':'system','panels':[
            {'id':'my-panel','title':'Ref Non-Descendant','kind':'stat',
             'source':'metric','metric_codes':[forbidden]}]}
        assert admin.post('/api/dashboard-builder', headers=current,
                          json=dash).status_code in (404,422)


def test_cross_unit_previews_statuses(site):
    admin, _, head, units = site
    ulp=as_unit(head,units['other'])
    day='2026-11-11'
    assert write(admin,head,units['kp'],day,{'kp_load':0}).status_code == 200
    report=admin.post('/api/report-builder/preview',headers=ulp,json={
        'blocks':[{'id':'source','kind':'stat','title':'Beban Kantor Pelayanan',
                   'metric_codes':['kp_load']}], 'start':day,'end':day})
    assert report.status_code == 200,report.text
    assert report.json()['source_status']['counts']['draft'] == 1
    assert report.json()['blocks'][0]['value'] == 0
    exp={'start':day,'end':day,'columns':['tanggal','kp_load'],
         'granularity':'hour','aggregation':'avg','format':'csv',
         'headers':{},'unit_overrides':{}}
    resp=admin.post('/api/data-export/preview',headers=ulp,json=exp)
    assert resp.status_code == 200,resp.text
    assert resp.json()['source_status']['counts']['draft'] == 1
    role=admin.get('/api/unit-references/same-role?role_key=system.load',headers=ulp)
    assert role.status_code == 200
    assert all(item['source'] for item in role.json()['operands'])


def test_topology_box_can_read_child_not_peer(site):
    admin, _, head, units=site
    owner=as_unit(head, units['other'])
    def layout(code):
        return {'canvas':{'w':1600,'h':900,'grid':10},'symbols':[], 'wires':[],
                'areas':[], 'boxes':[{'id':'sourcebox','kind':'metric',
                    'x':20,'y':20,'w':250,'title':'Beban anak','asset_code':None,
                    'metric_codes':[code],'decimals':2,'show_unit':True,
                    'leader':False,'sparkline':False,'locked':False,
                    'rule_id':None,'anchor_symbol_id':None}]}
    bad=admin.post('/api/topology',headers=owner,json={
        'name':'Diagram Peer Terlarang','layout':layout('foreign_kp_load')})
    assert bad.status_code == 422, bad.text
    good=admin.post('/api/topology',headers=owner,json={
        'name':'Diagram KP Turunan','layout':layout('kp_load')})
    assert good.status_code == 201, good.text
    day='2026-11-12'
    assert write(admin,head,units['kp'],day,{'kp_load':0}).status_code == 200
    reading=admin.get(f'/api/topology/{good.json()["id"]}/data?day={day}&hour=0',headers=owner)
    assert reading.status_code == 200, reading.text
    assert reading.json()['source_status']['counts']['draft'] == 1


def test_source_and_recap_share_one_transaction(site, monkeypatch):
    import pytest
    from app.modules.records import entry
    admin, Session, head, units = site
    day='2026-11-13'
    assert formula(admin,head,units['other'],'atomic_ulp_kw',
                   'SUM(other_load, kp_load)').status_code == 201
    with Session() as db:
        before=db.query(HourRecord).count(),db.query(Reading).count()
    def fail_after_source_write(*args, **kwargs):
        raise RuntimeError('Simulasi kegagalan hitung ulang')
    monkeypatch.setattr(entry, 'recalculate', fail_after_source_write)
    with pytest.raises(RuntimeError, match='Simulasi'):
        write(admin,head,units['kp'],day,{'kp_load':8})
    with Session() as db:
        assert (db.query(HourRecord).count(),db.query(Reading).count()) == before
    assert reading(Session,'kp_load',day) is None
