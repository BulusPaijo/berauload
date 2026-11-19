"""Stage 9e-1/2: advice for overloaded gardu (swap transformer / move load). Read-only."""
from fastapi.testclient import TestClient
from app import main
from app.modules.substations import advice_engine as eng
from app.modules.substations.models_calc import GarduCalcRule
from app.modules.substations.models import SubstationMeasurement, SubstationMasterHistory
from test_stage4a_units import site, login, as_unit
from test_stage9a_substations import visit

S = '/api/substations'
LIMIT_A = 100 * 1000 / (1.732 * 400)     # mean phase current at 100% of a 100 kVA, 400 V (seed constants)


def make(v, vh, code, kva, lat, lon, loads, lines=2, unit=None):
    body = {'code': code, 'name': 'Gardu ' + code, 'power_kva': kva, 'phase': 3, 'line_count': lines,
            'ownership': 'PLN', 'purpose': 'UMUM'}
    if lat is not None:
        body.update(lat=lat, lon=lon)
    if unit:
        body['unit_id'] = unit
    made = v.post(S + '/master', headers=vh, json=body)
    assert made.status_code == 200, made.text
    gid = made.json()['id']
    if loads is not None:
        values = []
        for no, amp in enumerate(loads, 1):
            if amp is None:
                continue
            values += [{'code': c, 'line_no': no, 'value': amp} for c in ('I_R', 'I_S', 'I_T')]
            values.append({'code': 'I_N', 'line_no': no, 'value': 5})
        saved = v.put(S + '/measurements', headers=vh, json=visit(gid, values=values))
        assert saved.status_code == 200, saved.text
    return gid


def world(site):
    client, Session, admin, units = site
    return client, Session, admin, units


def test_engine_is_pure_and_threshold_free():
    """Bisection on a fake linear evaluator: the range comes from the callback, not a number in the engine."""
    def evaluate(node, adjust=None):
        v, a = {'kva': node['kva'], 'fase': 3.0}, {c: [node['lines'][1][c]] for c in eng.CURRENT_CODES}
        for c in eng.CURRENT_CODES:
            v[f'{c}_j1'] = node['lines'][1][c]
        if adjust:
            adjust(v, a)
        persen = v['i_r_j1'] * 1.0
        return {'persen': persen, 'overload': persen > node['limit']}
    mk = lambda i, amp, limit: {'id': i, 'code': f'G{i}', 'name': 'x', 'kva': 100.0, 'phase': 3, 'limit': limit,
                                'line_count': 1, 'lines': {1: {'i_r': amp, 'i_s': amp, 'i_t': amp, 'i_n': None}}}
    x, z = mk(1, 150.0, 100.0), mk(2, 20.0, 100.0)
    option = eng.move_option(evaluate, x, z, 1)
    assert option['feasible'] and (option['p_min'], option['p_max']) == (34, 53)
    assert eng.move_option(evaluate, x, mk(3, 99.0, 100.0), 1)['feasible'] is False   # too little room
    assert eng.is_ok({'overload': None}) is False and eng.is_ok(None) is False         # NULL is never "fine"
    assert eng.movable_lines({'lines': {1: {'i_r': 0.0, 'i_s': 0.0, 'i_t': 0.0}, 2: {'i_r': 1.0, 'i_s': None, 'i_t': 1.0}}}) == []
    assert eng.distance_km(-1.5, 117.4, -1.5, 117.4) == 0


def test_swap_and_move_ranges_exclusions_and_scope(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v, TestClient(main.app) as k, TestClient(main.app) as m:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        x = make(v, vh, 'X1', 100, 2.0000, 117.0000, [100, 80])               # 180 A mean -> overloaded
        z1 = make(v, vh, 'Z1', 200, 2.0050, 117.0000, [60, 0])                # large and light
        z2 = make(v, vh, 'Z2', 100, 2.0100, 117.0000, [100, 0])               # same size, half full
        make(v, vh, 'NOCOORD', 100, None, None, [10, 0])
        make(v, vh, 'NOMEAS', 100, 2.0020, 117.0000, None)
        make(v, vh, 'GAP', 100, 2.0030, 117.0000, [30, None])                 # a line left empty -> NULL
        kp = make(v, vh, 'KPZ', 160, 2.0200, 117.0000, [20, 0], unit=units['kp'])
        foreign = make(client, as_unit(admin, units['home']), 'FOR1', 400, 2.0001, 117.0, [1, 0])
        r = v.get(f'{S}/advice/{x}', headers=vh)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a['available'] and a['overload'] is True and a['basis']['state'] == 'draft'
        assert abs(a['basis']['persen'] - 180 * 1.732 * 400 / 1000) < 0.2
        swaps = {o['target']['code']: o for o in a['swap']}
        assert swaps['Z1']['feasible'] and swaps['Z1']['x_after'] < 100 and swaps['Z1']['z_after'] < 100
        assert swaps['Z2']['feasible'] is False and 'tetap overload' in swaps['Z2']['reason']
        assert 'FOR1' not in swaps and 'NOCOORD' not in swaps and 'NOMEAS' not in swaps   # other ULP / no data
        assert swaps['KPZ']['target']['distance_km'] > 0                                   # KP of the same ULP joins
        moves = {(o['target']['code'], o['line_no']): o for o in a['move']}
        z2m = moves[('Z2', 1)]
        assert z2m['feasible'] and z2m['p_min'] == 36 and z2m['p_max'] == 44, z2m
        assert moves[('Z1', 1)]['p_min'] == 36 and moves[('Z1', 1)]['p_max'] == 100
        assert (moves[('Z2', 2)]['p_min'], moves[('Z2', 2)]['p_max']) == (45, 55)         # line 2 is smaller: needs a bigger share
        assert moves[('Z1', 2)]['feasible'] and moves[('Z1', 2)]['p_max'] == 100
        assert a['excluded']['tanpa_koordinat'] == 1 and a['excluded']['tanpa_pengukuran'] == 1
        assert a['excluded']['tidak_dapat_dinilai'] == 1                                  # GAP: NULL is not 0
        assert any(a['move'][i]['feasible'] for i in range(len(a['move'])))
        assert [o['feasible'] for o in a['swap']] == sorted([o['feasible'] for o in a['swap']], reverse=True)
        # review: before/after for a chosen portion, recomputed by the server
        ok = v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'move', 'target_id': z2, 'line': 1, 'portion': 40}).json()
        assert ok['ok_after'] is True and ok['sides'][0]['before']['overload'] is True
        assert abs(ok['sides'][0]['after']['persen'] - 140 * 1.732 * 0.4) < 0.2
        assert ok['sides'][0]['lines_after'][0]['i_r'] == 60 and ok['sides'][1]['lines_after'][0]['i_r'] == 140
        low = v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'move', 'target_id': z2, 'line': 1, 'portion': 30}).json()
        assert low['ok_after'] is False and low['sides'][0]['after']['overload'] is True
        sw = v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'swap', 'target_id': z1}).json()
        assert sw['ok_after'] and sw['sides'][0]['kva_after'] == 200 and sw['sides'][1]['kva_after'] == 100
        assert v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'swap', 'target_id': foreign}).status_code == 404
        assert v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'move', 'target_id': z2, 'line': 1}).status_code == 422
        # scope: a KP user cannot read the ULP's gardu; UP3 management may read
        kh = as_unit(login(k, 'operator_kp'), units['kp'])
        assert k.get(f'{S}/advice/{x}', headers=kh).status_code == 404
        assert k.get(f'{S}/advice/{kp}', headers=kh).status_code in (200,)                # own gardu: no coordinates needed to answer
        mh = login(m, 'management_root')
        assert m.get(f'{S}/advice/{x}', headers=mh).status_code == 200


def test_threshold_follows_admin_rule_and_nothing_is_written(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        x = make(v, vh, 'T1', 100, 2.0, 117.0, [100, 80])
        make(v, vh, 'T2', 200, 2.001, 117.0, [60, 0])
        with Session() as db:
            before = (db.query(SubstationMeasurement).count(), db.query(SubstationMasterHistory).count())
        assert v.get(f'{S}/advice/{x}', headers=vh).json()['overload'] is True
        v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'swap', 'target_id': 2})
        with Session() as db:
            assert (db.query(SubstationMeasurement).count(), db.query(SubstationMasterHistory).count()) == before
            rule = db.query(GarduCalcRule).filter_by(code='overload').first()
            rule.expression = 'persen_beban > 150'                                     # admin raises the limit
            db.commit()
        a = v.get(f'{S}/advice/{x}', headers=vh).json()
        assert a['overload'] is False and a['swap'] == [] and 'tidak overload' in a['reason']


def test_no_measurement_and_no_coordinates_are_reported(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        empty = make(v, vh, 'E1', 100, 2.0, 117.0, None)
        assert v.get(f'{S}/advice/{empty}', headers=vh).json()['reason'] == 'Gardu ini belum punya pengukuran'
        nocoord = make(v, vh, 'E2', 100, None, None, [100, 80])
        r = v.get(f'{S}/advice/{nocoord}', headers=vh).json()
        assert r['available'] is False and 'koordinat' in r['reason']
        gap = make(v, vh, 'E3', 100, 2.0, 117.0, [100, None])
        assert 'tidak dapat dinilai' in v.get(f'{S}/advice/{gap}', headers=vh).json()['reason']
        assert v.get(f'{S}/advice/999999', headers=vh).status_code == 404


from datetime import date
TODAY = date.today().isoformat()
A = '/api/substations/advice-followups'
F = '/api/substations/followups'


def mk_world(v, vh):
    x = make(v, vh, 'P1', 100, 2.0, 117.0, [100, 80])
    z1 = make(v, vh, 'Q1', 200, 2.005, 117.0, [60, 0])
    z2 = make(v, vh, 'Q2', 100, 2.01, 117.0, [100, 0])
    return x, z1, z2


def test_plan_followup_is_recomputed_and_guarded(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v, TestClient(main.app) as o, TestClient(main.app) as k:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        x, z1, z2 = mk_world(v, vh)
        made = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1, 'priority': 'tinggi'})
        assert made.status_code == 200, made.text
        row = made.json()
        assert row['type_code'] == 'tukar_trafo' and row['type_name'] == 'Tukar trafo' and row['status'] == 'terbuka'
        assert row['plan']['sides'][0]['after']['overload'] is False and row['plan']['applied'] is None
        assert 'Tukar trafo P1 (100 kVA) dengan Q1 (200 kVA)' in row['note']
        assert v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1}).status_code == 409
        assert v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z2}).status_code == 422
        bad = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'move', 'target_id': z2, 'line_no': 1, 'portion': 30})
        assert bad.status_code == 422 and 'belum menghilangkan overload' in bad.json()['detail']
        assert v.post(A, headers=vh, json={'substation_id': x, 'kind': 'move', 'target_id': z2}).status_code == 422
        mv = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'move', 'target_id': z2, 'line_no': 1, 'portion': 40})
        assert mv.status_code == 200 and mv.json()['type_name'] == 'Pindah beban' and mv.json()['plan']['range'] == [36, 44]
        listed = v.get(F, headers=vh).json()
        assert {i['type_code'] for i in listed['items']} == {'tukar_trafo', 'pindah_beban'}
        kh = as_unit(login(k, 'operator_kp'), units['kp'])
        assert k.post(A, headers=kh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1}).status_code == 404
        oh = as_unit(login(o, 'operator_u'), units['other'])
        assert o.post(A, headers=oh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1, 'note': 'ulang'}).status_code == 409


def done(v, vh, row):
    patch = v.patch(f"{F}/{row['id']}", headers=vh, json={
        'type_code': row['type_code'], 'priority': row['priority'], 'status': 'selesai',
        'note': row['note'], 'expected_version': row['version']})
    assert patch.status_code == 200, patch.text
    return patch.json()


def test_apply_swap_updates_master_history_audit_and_keeps_old_measurements(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v, TestClient(main.app) as o:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        oh = as_unit(login(o, 'operator_u'), units['other'])
        x, z1, _ = mk_world(v, vh)
        row = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1}).json()
        body = {'effective_on': TODAY, 'expected_version': row['version'], 'confirm': True}
        assert v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json=body).status_code == 409    # not finished yet
        row = done(v, vh, row)
        body['expected_version'] = row['version']
        assert o.post(f"{A}/{row['id']}/apply-swap", headers=oh, json=body).status_code == 403    # operator is not master manager
        assert v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json={**body, 'confirm': False}).status_code == 422
        assert v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json={**body, 'effective_on': '2999-01-01'}).status_code == 422
        assert v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json={**body, 'expected_version': 99}).status_code == 409
        with Session() as db:
            snapshots = sorted((m.substation_id, float(m.snapshot_power_kva)) for m in db.query(SubstationMeasurement))
        ok = v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json=body)
        assert ok.status_code == 200, ok.text
        masters = {m['id']: m for m in ok.json()['masters']}
        assert masters[x]['power_kva'] == 200 and masters[z1]['power_kva'] == 100
        assert ok.json()['followup']['plan']['applied']['effective_on'] == TODAY
        with Session() as db:
            assert sorted((m.substation_id, float(m.snapshot_power_kva)) for m in db.query(SubstationMeasurement)) == snapshots
            hist = db.query(SubstationMasterHistory).order_by(SubstationMasterHistory.id.desc()).limit(2).all()
            assert {h.substation_id for h in hist} == {x, z1} and all(str(h.effective_on) == TODAY for h in hist)
            from app.db import AuditLog
            acts = [a.action for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(6)]
            assert acts.count('substation_master_update') >= 2 and 'gardu_followup' in acts
        assert v.post(f"{A}/{row['id']}/apply-swap", headers=vh, json={**body, 'expected_version': row['version'] + 1}).status_code == 409
        after = v.get(f'{S}/advice/{x}', headers=vh).json()
        assert after['overload'] is False and after['basis']['kva_changed'] is True        # bigger trafo now, old reading kept


def test_apply_refuses_when_trafo_changed_after_plan(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        x, z1, _ = mk_world(v, vh)
        row = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z1}).json()
        row = done(v, vh, row)
        assert v.patch(f'{S}/master/{z1}', headers=vh, json={'power_kva': 250}).status_code == 200
        res = v.post(f"{A}/{row['id']}/apply-swap", headers=vh,
                     json={'effective_on': TODAY, 'expected_version': row['version'], 'confirm': True})
        assert res.status_code == 409 and 'berubah sejak rencana' in res.json()['detail']
        move = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'move', 'target_id': z1, 'line_no': 1, 'portion': 50}).json()
        move = done(v, vh, move)
        res = v.post(f"{A}/{move['id']}/apply-swap", headers=vh,
                     json={'effective_on': TODAY, 'expected_version': move['version'], 'confirm': True})
        assert res.status_code == 422                                                      # only swaps touch the master


def test_migration_idempotent_and_keeps_admin_edits(site):
    client, Session, admin, units = world(site)
    from sqlalchemy import inspect
    from app.modules.formulas.models import SchemaMigration
    from app.modules.substations.advice_migrations import run, VERSION
    from app.modules.substations.followup_models import GarduFollowupType
    engine = Session.kw['bind']
    run(engine); run(engine)
    assert 'plan' in {c['name'] for c in inspect(engine).get_columns('gardu_followups')}
    with Session() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        db.query(GarduFollowupType).filter_by(code='tukar_trafo').first().name = 'Tukar trafo (diubah admin)'
        db.query(SchemaMigration).filter_by(version=VERSION).delete()
        db.commit()
    run(engine)
    with Session() as db:
        assert db.query(GarduFollowupType).filter_by(code='tukar_trafo').count() == 1
        assert db.query(GarduFollowupType).filter_by(code='tukar_trafo').first().name == 'Tukar trafo (diubah admin)'
        assert db.query(GarduFollowupType).filter_by(code='pindah_beban').count() == 1


def put(v, vh, gid, session, day, amps):
    values = []
    for no, amp in enumerate(amps, 1):
        values += [{'code': c, 'line_no': no, 'value': amp} for c in ('I_R', 'I_S', 'I_T')]
    r = v.put(S + '/measurements', headers=vh, json={'substation_id': gid, 'measured_on': day, 'session': session,
                                                       'revision': None, 'values': values})
    assert r.status_code == 200, r.text
    return r.json()['id']


def test_worst_recent_session_is_used_like_analisa_and_screen_measurement_wins(site):
    client, Session, admin, units = world(site)
    with TestClient(main.app) as v:
        vh = as_unit(login(v, 'verifier_u'), units['other'])
        x = make(v, vh, 'S1', 100, 2.0, 117.0, None)
        night = put(v, vh, x, 'MALAM', '2034-01-01', [100, 80])      # older but heavy
        noon = put(v, vh, x, 'SIANG', '2034-01-05', [50, 40])        # newer but light
        z = make(v, vh, 'S2', 200, 2.005, 117.0, [60, 0])
        put(v, vh, z, 'SIANG', '2034-01-03', [20, 0])                # target: light at noon, heavier at night
        put(v, vh, z, 'MALAM', '2034-01-03', [90, 0])
        a = v.get(f'{S}/advice/{x}', headers=vh).json()
        assert a['overload'] is True and a['basis']['session'] == 'MALAM' and a['basis']['measurement_id'] == night
        zt = [o for o in a['swap'] if o['target']['code'] == 'S2'][0]['target']
        assert zt['session'] == 'MALAM' and abs(zt['persen_now'] - 90 * 1.732 * 400 / 1000 / 2) < 0.2   # worst session of the target
        light = v.get(f'{S}/advice/{x}', headers=vh, params={'measurement_id': noon}).json()
        assert light['overload'] is False and light['basis']['measurement_id'] == noon                  # the one on screen wins
        assert v.get(f'{S}/advice/{x}', headers=vh, params={'measurement_id': 999999}).status_code == 422
        other = put(v, vh, z, 'MALAM', '2034-01-09', [10, 0])
        assert v.get(f'{S}/advice/{x}', headers=vh, params={'measurement_id': other}).status_code == 422   # someone else's reading
        rv = v.get(f'{S}/advice/{x}/review', headers=vh, params={'kind': 'swap', 'target_id': z, 'measurement_id': night})
        assert rv.status_code == 200 and rv.json()['source']['session'] == 'MALAM'
        plan = v.post(A, headers=vh, json={'substation_id': x, 'kind': 'swap', 'target_id': z, 'measurement_id': night}).json()
        assert plan['measurement_id'] == night and plan['plan']['basis']['source_session'] == 'MALAM'
