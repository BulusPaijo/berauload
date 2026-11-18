"""Stage 9d-4: ULP manages and fills its KPs' gardu; tegangan ujung per gardu migration."""
import io
from fastapi.testclient import TestClient
from openpyxl import Workbook
from app import main
from app.modules.formulas.models import SchemaMigration
from app.modules.substations import end_voltage_migration as ev
from app.modules.substations.followup_models import GarduFollowup
from app.modules.substations.models import Substation, SubstationMeasurement, SubstationParam, SubstationValue
from app.modules.substations.models_calc import GarduCalcColumn, GarduCalcSettings
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import visit

S = '/api/substations'


def gardu(code, unit=None, feeder=None, lines=2):
    body = {'code': code, 'name': 'Gardu ' + code, 'power_kva': 100, 'phase': 3, 'line_count': lines,
            'ownership': 'PLN', 'purpose': 'UMUM'}
    if unit:
        body['unit_id'] = unit
    if feeder:
        body['feeder_id'] = feeder
    return body


def test_scope_and_master_rights_in_ulp_family(site):
    client, Session, admin, units = site
    with TestClient(main.app) as v, TestClient(main.app) as o, TestClient(main.app) as k:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        oh = as_unit(login(o, 'operator_u'), units['other'])
        kh = as_unit(login(k, 'operator_kp'), units['kp'])
        sv = v.get(S + '/scope', headers=vh).json()
        assert set(sv['data_unit_ids']) == {units['other'], units['kp']} and sv['can_manage_master']
        assert o.get(S + '/scope', headers=oh).json()['can_manage_master'] is False
        assert k.get(S + '/scope', headers=kh).json()['data_unit_ids'] == [units['kp']]
        feeder = v.post(S + '/feeders', headers=vh, json={'code': 'F1', 'name': 'Penyulang 1'})
        assert feeder.status_code == 200, feeder.text
        fid = feeder.json()['id']
        assert o.post(S + '/feeders', headers=oh, json={'code': 'F2', 'name': 'x'}).status_code == 403
        assert v.post(S + '/feeders', headers=as_unit(vh, units['kp']), json={'code': 'F3', 'name': 'x'}).status_code == 403
        made = v.post(S + '/master', headers=vh, json=gardu('KP001', units['kp'], fid))
        assert made.status_code == 200, made.text
        assert made.json()['unit_id'] == units['kp']          # placed in the KP, ULP feeder accepted
        own = v.post(S + '/master', headers=vh, json=gardu('ULP001', feeder=fid)).json()
        assert own['unit_id'] == units['other']
        assert v.post(S + '/master', headers=vh, json=gardu('KP001')).status_code == 409   # family-wide code
        assert v.post(S + '/master', headers=vh, json=gardu('X1', units['foreign_kp'])).status_code == 403
        assert o.post(S + '/master', headers=oh, json=gardu('O1')).status_code == 403
        assert k.post(S + '/master', headers=kh, json=gardu('K1')).status_code == 403
        assert k.get(S + '/feeders', headers=kh).json()[0]['id'] == fid               # KP sees ULP feeders
        listed = {r['code']: r['unit_id'] for r in o.get(S + '/master', headers=oh).json()['items']}
        assert listed == {'KP001': units['kp'], 'ULP001': units['other']}
        assert [r['code'] for r in k.get(S + '/master', headers=kh).json()['items']] == ['KP001']
        kp_id = made.json()['id']
        edit = v.patch(f'{S}/master/{kp_id}', headers=as_unit(vh, units['kp']), json={'name': 'Diubah dari KP'})
        assert edit.status_code == 200 and edit.json()['master']['name'] == 'Diubah dari KP'
        assert v.patch(f'{S}/master/{kp_id}', headers=as_unit(vh, units['kp']),
                       json={'unit_id': units['other']}).status_code == 403             # KP context cannot move up


def test_ulp_fills_kp_data_and_move_carries_history(site):
    client, Session, admin, units = site
    with TestClient(main.app) as v, TestClient(main.app) as o, TestClient(main.app) as k:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        oh = as_unit(login(o, 'operator_u'), units['other'])
        kh = as_unit(login(k, 'operator_kp'), units['kp'])
        kp_gardu = v.post(S + '/master', headers=vh, json=gardu('KP002', units['kp'])).json()['id']
        ulp_gardu = v.post(S + '/master', headers=vh, json=gardu('ULP002')).json()['id']
        rec = o.put(S + '/measurements', headers=oh, json=visit(kp_gardu, values=[{'code': 'I_R', 'line_no': 1, 'value': 50}]))
        assert rec.status_code == 200, rec.text
        mid = rec.json()['measurement']['id']
        assert rec.json()['measurement']['unit_id'] == units['kp']                    # data stays owned by KP
        assert k.put(S + '/measurements', headers=kh, json=visit(ulp_gardu)).status_code == 404
        follow = o.post(S + '/followups', headers=oh, json={'substation_id': kp_gardu, 'type_code': 'pantau'})
        assert follow.status_code == 200 and follow.json()['unit_id'] == units['kp']
        assert k.get(S + '/followups', headers=kh).json()['total'] == 1
        assert o.post(S + '/measurements/actions', headers=oh, json={'ids': [mid], 'action': 'verify'}).status_code == 403
        ver = v.post(S + '/measurements/actions', headers=vh, json={'ids': [mid], 'action': 'verify'})
        assert ver.status_code == 200 and ver.json()['results'][0]['status'] != 'error', ver.text
        moved = v.patch(f'{S}/master/{kp_gardu}', headers=vh, json={'unit_id': units['other']})
        assert moved.status_code == 200 and moved.json()['master']['unit_id'] == units['other']
        with Session() as db:
            assert db.get(SubstationMeasurement, mid).unit_id == units['other']
            assert db.query(GarduFollowup).filter_by(substation_id=kp_gardu).one().unit_id == units['other']
        assert k.get(S + '/followups', headers=kh).json()['total'] == 0
        bulk = v.patch(S + '/master/bulk', headers=vh, json={'ids': [kp_gardu, ulp_gardu], 'changes': {'unit_id': units['kp']}})
        assert [r['status'] for r in bulk.json()['results']] == ['updated', 'updated']
        assert k.get(S + '/master', headers=kh).json()['total'] == 2


def test_master_import_unit_column_and_template(site):
    client, Session, admin, units = site
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        v.post(S + '/feeders', headers=vh, json={'code': 'F1', 'name': 'Penyulang 1'})
        wb = Workbook(); ws = wb.active
        ws.append(['kode', 'nama', 'penyulang', 'power_kva', 'phase', 'line_count', 'unit'])
        ws.append(['IMP1', 'Impor KP', 'F1', 100, 3, 2, 'kp_synthetic'])
        ws.append(['IMP2', 'Impor ULP', 'F1', 50, 3, 1, ''])
        ws.append(['IMP3', 'Salah unit', 'F1', 50, 3, 1, 'kp_foreign'])
        buf = io.BytesIO(); wb.save(buf)
        pre = v.post(S + '/master/import/preview', headers=vh, files={'file': ('m.xlsx', buf.getvalue())})
        assert pre.status_code == 200, pre.text
        assert pre.json()['rows'][2]['errors'] and not pre.json()['new_feeders']
        res = v.post(S + '/master/import/apply', headers=vh, json={'token': pre.json()['token']})
        assert [r['status'] for r in res.json()['results']] == ['created', 'created', 'error']
        with Session() as db:
            got = {s.code: s.unit_id for s in db.query(Substation)}
        assert got['IMP1'] == units['kp'] and got['IMP2'] == units['other']
        tpl = v.get(S + '/master/template', headers=vh)
        from openpyxl import load_workbook
        rows = list(load_workbook(io.BytesIO(tpl.content)).active.iter_rows(values_only=True))
        assert rows[0][-1] == 'unit' and {r[0]: r[-1] for r in rows[1:]}['IMP1'] == 'kp_synthetic'


def _old_layout(Session):
    with Session() as db:
        for p in db.query(SubstationParam).filter(SubstationParam.code.in_(ev.CODES)):
            p.scope = 'line'
        col = db.query(GarduCalcColumn).filter_by(code='v_ujung_min').one()
        col.expression = col.default_expression = ev.OLD
        col.default_snapshot = {**(col.default_snapshot or {}), 'expression': ev.OLD}
        db.query(SchemaMigration).filter_by(version=ev.VERSION).delete()
        db.commit()


def test_end_voltage_migration_keeps_lowest_archives_all_and_respects_admin_formula(site):
    client, Session, admin, units = site
    engine = Session.kw['bind']
    with Session() as db:
        assert {p.scope for p in db.query(SubstationParam).filter(SubstationParam.code.in_(ev.CODES))} == {'substation'}
    _old_layout(Session)
    h = as_unit(admin, units['kp'])
    client.post(S + '/feeders', headers=h, json={'code': 'F1', 'name': 'P'})
    gid = client.post(S + '/master', headers=h, json=gardu('EV1')).json()['id']
    rec = client.put(S + '/measurements', headers=h, json=visit(gid, values=[
        {'code': 'V_END_RN', 'line_no': 1, 'value': 205}, {'code': 'V_END_RN', 'line_no': 2, 'value': 199},
        {'code': 'V_END_SN', 'line_no': 2, 'flag': 'PUTUS'}, {'code': 'V_END_TN', 'line_no': 1, 'value': 210}]))
    assert rec.status_code == 200, rec.text
    mid = rec.json()['measurement']['id']
    with Session() as db:
        version = db.get(GarduCalcSettings, 1).version
    assert ev.run(engine).startswith('converted (4 ')
    assert ev.run(engine) is None
    with Session() as db:
        p = {x.code: x for x in db.query(SubstationParam).filter(SubstationParam.code.in_(ev.CODES))}
        assert {x.scope for x in p.values()} == {'substation'}
        got = {(v.param_id, v.line_no): (v.value, v.flag) for v in db.query(SubstationValue).filter_by(measurement_id=mid)
               if v.param_id in {x.id for x in p.values()}}
        assert got == {(p['V_END_RN'].id, 0): (199, None), (p['V_END_SN'].id, 0): (None, 'PUTUS'),
                       (p['V_END_TN'].id, 0): (210, None)}
        assert len(db.execute(ev.archive.select()).all()) == 4
        col = db.query(GarduCalcColumn).filter_by(code='v_ujung_min').one()
        assert col.expression == ev.NEW == col.default_snapshot['expression']
        assert db.get(GarduCalcSettings, 1).version == version     # results numerically unchanged
    again = client.put(S + '/measurements', headers=h, json=visit(gid, revision=rec.json()['measurement']['revision'],
                       values=[{'code': 'V_END_RN', 'line_no': 0, 'value': 200}]))
    assert again.status_code == 200, again.text
    assert client.put(S + '/measurements', headers=h, json=visit(gid, revision=again.json()['measurement']['revision'],
                      values=[{'code': 'V_END_RN', 'line_no': 1, 'value': 200}])).status_code == 422


def test_end_voltage_migration_never_overwrites_admin_formula(site):
    client, Session, admin, units = site
    _old_layout(Session)
    with Session() as db:
        db.query(GarduCalcColumn).filter_by(code='v_ujung_min').one().expression = 'MIN_JURUSAN(v_end_rn)'
        db.commit()
    assert ev.run(Session.kw['bind']).startswith('converted')
    with Session() as db:
        col = db.query(GarduCalcColumn).filter_by(code='v_ujung_min').one()
        assert col.expression == 'MIN_JURUSAN(v_end_rn)' and col.default_expression == ev.NEW
