"""V1.5.0 stage 1: fully isolated SQLite, no production data or inferred network."""
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix='berauload_topology_'))
os.environ['DATABASE_URL'] = 'sqlite:///' + str(root / 'qa.db')
os.environ['UPLOAD_DIR'] = str(root / 'uploads')
os.environ['ADMIN_PASSWORD'] = 'Test-Topology-Password-2026'

from fastapi.testclient import TestClient
from app.main import app
from app.db import AuditLog, HourRecord, Metric, Reading, SessionLocal, engine
from app.modules.engineering.models import EngineeringRule
from app.modules.formulas.models import SchemaMigration
from app.modules.topology.migrations import VERSION, run as migrate
from app.modules.topology.models import TopologyDiagram, TopologyRevision
from app.modules.topology.service import EMPTY_LAYOUT, validate_layout, TopologyError

CAP = 'daya_pasok_pembangkit_kw'
LOAD = 'beban_sistem_kw'


def login(client, username='admin', password=None):
    result = client.post('/api/auth/login', json={
        'username': username, 'password': password or os.environ['ADMIN_PASSWORD']})
    assert result.status_code == 200, result.text
    return {'X-CSRF-Token': result.json()['csrf']}


def box(id='box-1', codes=None, asset=None, rule=None):
    return {'id': id, 'kind': 'metric', 'x': 20, 'y': 30, 'w': 200,
            'title': 'Beban Sistem', 'asset_code': asset, 'metric_codes': codes or [LOAD],
            'decimals': 2, 'show_unit': True, 'leader': False,
            'sparkline': True, 'locked': False, 'rule_id': rule,
            'anchor_symbol_id': None}


def layout(*boxes):
    return {**EMPTY_LAYOUT, 'boxes': list(boxes)}


def create(client, headers, body=None):
    return client.post('/api/topology', headers=headers, json=body or {
        'name': 'Topologi QA', 'layout': layout(box())})


def test_empty_start_create_revision_and_optimistic_lock():
    with TestClient(app) as client:
        headers = login(client)
        assert client.get('/api/topology').json() == []
        first = client.post('/api/topology', headers=headers,
                            json={'name': 'Topologi Kosong'})
        assert first.status_code == 201, first.text
        row = first.json()
        assert row['layout'] == EMPTY_LAYOUT and row['version'] == 1
        assert client.get(f"/api/topology/{row['id']}").status_code == 200
        update = client.put(f"/api/topology/{row['id']}", headers=headers, json={
            'name': 'Topologi Kosong Terbaru', 'layout': layout(box()),
            'expected_version': 1})
        assert update.status_code == 200, update.text
        assert update.json()['version'] == 2
        stale = client.put(f"/api/topology/{row['id']}", headers=headers, json={
            'name': 'Tertinggal', 'layout': EMPTY_LAYOUT, 'expected_version': 1})
        assert stale.status_code == 409
        history = client.get(f"/api/topology/{row['id']}/revisions").json()
        assert [r['version'] for r in history] == [2, 1]
        restored = client.post(f"/api/topology/{row['id']}/restore-version",
                               headers=headers, json={'version': 1, 'expected_version': 2})
        assert restored.status_code == 200, restored.text
        assert restored.json()['version'] == 3
        assert restored.json()['layout'] == EMPTY_LAYOUT
        assert len(client.get(f"/api/topology/{row['id']}/revisions").json()) == 3


def test_bad_csrf_and_non_admin_write():
    with TestClient(app) as admin:
        headers = login(admin)
        missing = admin.post('/api/topology', json={'name': 'No CSRF'})
        assert missing.status_code == 403
        user = admin.post('/api/users', headers=headers, json={
            'username': 'topoview', 'display_name': 'Topologi Viewer',
            'password': 'Viewer-Test-Password-2026', 'role': 'management', 'accesses': _qa_grants('management')})
        assert user.status_code == 200, user.text
        created = create(admin, headers)
        assert created.status_code == 201, created.text
        id = created.json()['id']
        with TestClient(app) as viewer:
            view_header = login(viewer, 'topoview', 'Viewer-Test-Password-2026')
            assert viewer.get('/api/topology').status_code == 200
            from app.modules.org_units.repository import home_unit
            with SessionLocal() as db:
                home={'X-Unit-Id':str(home_unit(db).id)}
            assert viewer.get(f'/api/topology/{id}').status_code == 404
            assert viewer.get(f'/api/topology/{id}',headers=home).status_code == 200
            assert create(viewer, view_header).status_code == 403
            assert viewer.put(f'/api/topology/{id}', headers=view_header, json={
                'name': 'Tidak Bisa', 'layout': EMPTY_LAYOUT, 'expected_version': 1}).status_code == 403
            assert viewer.post(f'/api/topology/{id}/archive', headers=view_header).status_code == 403
            assert viewer.post(f'/api/topology/{id}/restore-version', headers=view_header, json={
                'version': 1, 'expected_version': 1}).status_code == 403


def test_layout_validation_catches_bad_references_and_geometry():
    with TestClient(app) as client:
        headers = login(client)
        for bad in [
            box(codes=['not_a_metric']),
            box(codes=['daya_mampu_sistem_kw']),
            box(codes=[LOAD] * 7),
            {**box(), 'x': 1600},
            {**box(), 'x': 11},
            {**box(), 'title': '<script>bad</script>'},
            {**box(), 'asset_code': 'not_existing'},
            {**box(), 'rule_id': 999999},
        ]:
            response = create(client, headers, {'name': 'Reject Validasi', 'layout': layout(bad)})
            assert response.status_code == 422, (bad, response.status_code, response.text)
        duplicate = create(client, headers, {'name': 'Duplicate', 'layout': layout(box(), box())})
        assert duplicate.status_code == 422
        invalid_wire = {**EMPTY_LAYOUT, 'wires': [{'id': 'line-1', 'points': [[0,0],[20,20]],
                                                   'level': '#FF0000'}]}
        assert create(client, headers, {'name': 'Invalid Wire', 'layout': invalid_wire}).status_code == 422
        breaker = {'id': 's-1', 'type': 'breaker', 'x': 10, 'y': 10,
                   'w': 40, 'h': 40, 'asset_code': None,
                   'label': 'PMT netral', 'rotation': 0}
        assert create(client, headers, {'name': 'Simbol tanpa status', 'layout': {
            **EMPTY_LAYOUT, 'symbols': [breaker]}}).status_code == 201


def test_data_zero_null_missing_hour_and_24h_series():
    with TestClient(app) as client:
        headers = login(client)
        response = create(client, headers, {'name': 'Hour Readings',
                    'layout': layout(box(codes=[CAP, LOAD]))})
        assert response.status_code == 201, response.text
        id = response.json()['id']
        day = date(2026, 11, 14)
        with SessionLocal() as db:
            m = db.query(Metric).filter_by(code=LOAD).first()
            record = HourRecord(day=day, hour=1,
                timestamp_utc=datetime(2026, 11, 13, 17, tzinfo=timezone.utc))
            db.add(record); db.flush()
            db.add(Reading(hour_id=record.id, metric_id=m.id, value=0, source='manual'))
            db.commit()
        at_one = client.get(f'/api/topology/{id}/data?day={day}&hour=1')
        assert at_one.status_code == 200, at_one.text
        assert at_one.json()['values'] == {CAP: None, LOAD: 0}
        assert at_one.json()['day_status'] == 'draft'
        absent = client.get(f'/api/topology/{id}/data?day={day}&hour=2')
        assert absent.status_code == 200 and absent.json()['values'][LOAD] is None
        assert client.get(f'/api/topology/{id}/data?day={day}&hour=24').status_code == 422
        series = client.get(f'/api/topology/{id}/series?day={day}')
        assert series.status_code == 200, series.text
        hourly = series.json()['series'][LOAD]
        assert len(hourly) == 24 and hourly[1]['value'] == 0
        assert hourly[0]['value'] is None and hourly[23]['value'] is None


def test_active_rule_uses_existing_engine_and_archive():
    with TestClient(app) as client:
        headers = login(client)
        with SessionLocal() as db:
            rule = EngineeringRule(code='topology_load_rule', name='QA Beban Sistem',
                expression=LOAD, unit='kW', direction='above',
                warning_threshold=10, critical_threshold=20,
                reference_note='Uji sintetis, bukan ambang teknis operasional',
                effective_from=date(2026, 1, 1), status='active', created_by=1,
                unit_id=db.query(Metric).filter_by(code=LOAD).one().unit_id)
            db.add(rule); db.commit(); rid = rule.id
        resp = create(client, headers, {'name': 'Active Rule',
                        'layout': layout(box(rule=rid))})
        assert resp.status_code == 201, resp.text
        id = resp.json()['id']
        result = client.get(f'/api/topology/{id}/data?day=2026-11-15&hour=0')
        assert result.status_code == 200, result.text
        assert result.json()['rules'][str(rid)] is None
        with SessionLocal() as db:
            metric = db.query(Metric).filter_by(code=LOAD).one()
            for hour, value in ((0, 0), (1, 15), (2, 25)):
                record = HourRecord(day=date(2026, 11, 15), hour=hour,
                    timestamp_utc=datetime(2026, 11, 14, 16 + hour,
                                           tzinfo=timezone.utc))
                db.add(record)
                db.flush()
                db.add(Reading(hour_id=record.id, metric_id=metric.id,
                               value=value, source='manual'))
            db.commit()
        for hour, status in ((0, 'normal'), (1, 'warning'), (2, 'critical')):
            response = client.get(f'/api/topology/{id}/data?day=2026-11-15&hour={hour}')
            assert response.status_code == 200, response.text
            assert response.json()['rules'][str(rid)] == status
        with SessionLocal() as db:
            before = db.query(Reading).count()
        archived = client.post(f'/api/topology/{id}/archive', headers=headers)
        assert archived.status_code == 200 and archived.json()['archived'] is True
        assert client.get(f'/api/topology/{id}').status_code == 404
        with SessionLocal() as db:
            assert db.query(Reading).count() == before
            assert db.query(AuditLog).filter_by(action='topology_archive').count() >= 1


def test_migration_idempotent_and_not_touching_readings():
    migrate(engine)
    migrate(engine)
    with SessionLocal() as db:
        assert db.query(SchemaMigration).filter_by(version=VERSION).count() == 1
        assert db.query(TopologyDiagram).count() >= 1
        for item in db.query(TopologyRevision):
            assert item.snapshot.get('layout') is not None


def test_reject_malformed_json_types_without_internal_error():
    base_symbol = {'id': 'sym-1', 'type': 'breaker', 'x': 0, 'y': 0,
                   'w': 10, 'h': 10, 'asset_code': None,
                   'label': 'PMT netral', 'rotation': 0}
    base_wire = {'id': 'line-1', 'points': [[0, 0], [10, 10]], 'level': '20kv'}
    base_box = box()
    valid = {**EMPTY_LAYOUT, 'symbols': [base_symbol], 'wires': [base_wire],
             'boxes': [base_box]}
    refs = ({}, {LOAD: ('kW', None)}, set())
    from copy import deepcopy
    import pytest
    for group, field, invalid in (('symbols', 'type', []),
                                  ('symbols', 'asset_code', []),
                                  ('wires', 'level', {}),
                                  ('boxes', 'kind', []),
                                  ('boxes', 'title', 'javascript:alert(1)'),
                                  ('symbols', 'label', '<script>bad</script>')):
        candidate = deepcopy(valid)
        candidate[group][0][field] = invalid
        with pytest.raises(TopologyError):
            validate_layout(candidate, *refs)


def test_stage3_editor_snapshot_save_cancel_and_data_unchanged():
    """Client cancel = no PUT; accepted snapshot is one immutable version."""
    with TestClient(app) as client:
        headers = login(client)
        first = client.post('/api/topology', headers=headers,
                            json={'name': 'Editor Tahap 3'})
        assert first.status_code == 201
        diagram_id = first.json()['id']
        source = client.get(f'/api/topology/{diagram_id}').json()
        assert source['layout'] == EMPTY_LAYOUT and source['version'] == 1
        draft = layout(box())
        # A local draft or cancel never calls PUT, therefore persisted layout stays empty.
        assert client.get(f'/api/topology/{diagram_id}').json()['layout'] == EMPTY_LAYOUT
        with SessionLocal() as db:
            before = db.query(Reading).count()
        saved = client.put(f'/api/topology/{diagram_id}', headers=headers, json={
            'name': 'Editor Tahap 3', 'description': 'Draf parameter',
            'expected_version': 1, 'layout': draft})
        assert saved.status_code == 200, saved.text
        assert saved.json()['layout']['boxes'][0]['metric_codes'] == [LOAD]
        assert saved.json()['version'] == 2
        stale = client.put(f'/api/topology/{diagram_id}', headers=headers, json={
            'name': 'Editor Tahap 3', 'expected_version': 1, 'layout': draft})
        assert stale.status_code == 409
        revisions = client.get(f'/api/topology/{diagram_id}/revisions').json()
        assert [item['version'] for item in revisions] == [2, 1]
        with SessionLocal() as db:
            assert db.query(Reading).count() == before


def test_stage4_visual_layout_persists_without_inferred_connectivity():
    """Symbols, authored wires and data boxes save as JSON; readings never change."""
    with TestClient(app) as client:
        headers = login(client)
        original = client.post('/api/topology', headers=headers,
                               json={'name': 'Tahap 4 tanpa seed'})
        assert original.status_code == 201, original.text
        id = original.json()['id']
        sym = {'id': 's-manual', 'type': 'breaker', 'x': 100, 'y': 120,
               'w': 120, 'h': 70, 'asset_code': None,
               'label': 'PMT visual netral', 'rotation': 0}
        visual_wire = {'id': 'w-1', 'points': [[20, 20], [20, 200], [240, 200]],
                       'level': 'unspecified'}
        summary = {**box('sum-1', codes=[LOAD, CAP]), 'kind': 'summary',
                   'title': 'Dua pembacaan', 'anchor_symbol_id': 's-manual',
                   'leader': True}
        ranking = {**box('rank-1', codes=[LOAD, CAP]), 'kind': 'ranking',
                   'title': 'Peringkat kW', 'y': 220}
        legend = {**box('legend-1'), 'kind': 'legend', 'metric_codes': [],
                  'title': 'Legenda', 'y': 400, 'sparkline': False}
        note = {**box('text-1'), 'kind': 'text', 'metric_codes': [],
                'title': 'Catatan gambar', 'y': 580, 'sparkline': False}
        config = {**EMPTY_LAYOUT, 'symbols': [sym], 'wires': [visual_wire],
                  'boxes': [summary, ranking, legend, note]}
        with SessionLocal() as db:
            before = db.query(Reading).count()
        response = client.put(f'/api/topology/{id}', headers=headers, json={
            'name': 'Tahap 4 tanpa seed', 'expected_version': 1, 'layout': config})
        assert response.status_code == 200, response.text
        assert response.json()['layout'] == config
        assert response.json()['version'] == 2
        assert client.get(f'/api/topology/{id}/data?day=2026-11-14&hour=10').json()[
            'values'] == {CAP: None, LOAD: None}
        assert client.get(f'/api/topology/{id}/series?day=2026-11-14').status_code == 200
        with SessionLocal() as db:
            assert db.query(Reading).count() == before
            assert db.query(AuditLog).filter_by(action='topology_update').count() >= 1


def test_stage4_rejects_mixed_unit_ranking_and_invalid_wires():
    with TestClient(app) as client:
        headers = login(client)
        from app.db import Asset
        with SessionLocal() as db:
            unit_codes = {m.unit: m.code for m in db.query(Metric).filter(Metric.active.is_(True))}
        assert 'kW' in unit_codes
        different = next((code for unit, code in unit_codes.items() if unit != 'kW'), None)
        if different:
            mixed = {**box(codes=[LOAD, different]), 'kind': 'ranking'}
            bad = create(client, headers, {'name': 'Mixed Units', 'layout': layout(mixed)})
            assert bad.status_code == 422, bad.text
        bad_wire = {'id': 'w-bad', 'points': [[10, 10], [10, 10]],
                    'level': 'unspecified'}
        rejected = create(client, headers, {'name': 'Duplicate Vertices',
                          'layout': {**EMPTY_LAYOUT, 'wires': [bad_wire]}})
        assert rejected.status_code == 422
        missing_summary = {**box(), 'kind': 'summary', 'metric_codes': []}
        assert create(client, headers, {'name': 'Missing Summary',
                      'layout': layout(missing_summary)}).status_code == 422
        forged_legend = {**box(), 'kind': 'legend', 'metric_codes': [LOAD]}
        assert create(client, headers, {'name': 'Forged Legend',
                      'layout': layout(forged_legend)}).status_code == 422


def test_stage4_1_busbar_resize_layout_remains_configuration_only():
    """Length is editable layout geometry, not a change to electrical readings/wires."""
    with TestClient(app) as client:
        headers = login(client)
        symbol = {'id': 'busbar-length', 'type': 'busbar', 'x': 200, 'y': 300,
                  'w': 180, 'h': 40, 'asset_code': None,
                  'label': 'Busbar rancangan', 'rotation': 0}
        wire = {'id': 'wire-separate', 'points': [[10, 10], [100, 10]],
                'level': 'unspecified'}
        initial = {**EMPTY_LAYOUT, 'symbols': [symbol], 'wires': [wire]}
        created = create(client, headers, {'name': 'Busbar panjang', 'layout': initial})
        assert created.status_code == 201, created.text
        with SessionLocal() as db:
            readings_before = db.query(Reading).count()
        changed = {**EMPTY_LAYOUT, 'symbols': [{**symbol, 'w': 650}], 'wires': [wire]}
        response = client.put(f"/api/topology/{created.json()['id']}", headers=headers,
                              json={'expected_version': 1, 'name': 'Busbar panjang',
                                    'layout': changed})
        assert response.status_code == 200, response.text
        assert response.json()['layout']['symbols'][0]['w'] == 650
        assert response.json()['layout']['wires'] == [wire]
        with SessionLocal() as db:
            assert db.query(Reading).count() == readings_before

# V1.5.0 Stage 4.2 — non-electrical Group Area and backward compatibility.
def _visual_area(id='area-1'):
    return {'id': id, 'x': 40, 'y': 50, 'w': 320, 'h': 260,
            'title': 'GH Kantor', 'border': 'dashed', 'color': 'blue',
            'opacity': 15, 'locked': False}


def test_stage42_area_validation_and_legacy_layout():
    import copy
    legacy = copy.deepcopy(EMPTY_LAYOUT)
    snapshot = copy.deepcopy(legacy)
    assert validate_layout(legacy, {}, {}, set()) == legacy
    assert legacy == snapshot and 'areas' not in legacy
    grouped = {**legacy, 'areas': [_visual_area()]}
    assert validate_layout(grouped, {}, {}, set())['areas'][0]['opacity'] == 15
    assert validate_layout(grouped, {}, {}, set()) != legacy
    assert validate_layout({**legacy, 'canvas': {'w': 12000, 'h': 9000, 'grid': 10}}, {}, {}, set())
    for patch in ({'color': '#ff00ff'}, {'border': '<script>'}, {'opacity': 13},
                  {'x': -10}, {'title': '<b>GH</b>'}, {'locked': 'false'},
                  {'w': 1600}):
        invalid = {**grouped, 'areas': [{**_visual_area(), **patch}]}
        try:
            validate_layout(invalid, {}, {}, set())
        except TopologyError:
            continue
        raise AssertionError(f'Area invalid accepted: {patch}')
    try:
        validate_layout({**grouped, 'areas': [_visual_area(), _visual_area()]}, {}, {}, set())
    except TopologyError:
        pass
    else:
        raise AssertionError('Duplicate area IDs accepted')
    try:
        validate_layout({**grouped, 'areas': [_visual_area(f'area-{i}') for i in range(101)]}, {}, {}, set())
    except TopologyError:
        pass
    else:
        raise AssertionError('Area count 101 accepted')


def test_stage42_area_api_revision_without_electrical_writes():
    with TestClient(app) as client:
        headers = login(client)
        with SessionLocal() as db:
            baseline = db.query(Reading).count()
        grouped = {**EMPTY_LAYOUT, 'areas': [_visual_area()]}
        created = create(client, headers, {'name': 'Area Non Listrik', 'layout': grouped})
        assert created.status_code == 201, created.text
        diagram_id = created.json()['id']
        old = client.get(f'/api/topology/{diagram_id}').json()
        assert old['layout']['areas'] == grouped['areas']
        modified = {**grouped, 'areas': [{**_visual_area(), 'border': 'solid', 'opacity': 0}]}
        saved = client.put(f'/api/topology/{diagram_id}', headers=headers,
                           json={'name': 'Area Non Listrik', 'layout': modified, 'expected_version': 1})
        assert saved.status_code == 200, saved.text
        assert saved.json()['version'] == 2
        assert client.get(f'/api/topology/{diagram_id}/revisions').json()[0]['snapshot']['layout']['areas'] == modified['areas']
        with SessionLocal() as db:
            assert db.query(Reading).count() == baseline
        assert client.get(f'/api/topology/{diagram_id}/data?day=2026-11-15&hour=4').json()['values'] == {}


def _qa_grants(role):
    """Updated synthetic fixture: Stage 4c requires explicit unit grants."""
    from app.modules.org_units.repository import home_unit, root
    with SessionLocal() as db:
        unit = root(db) if role == 'management' else home_unit(db)
        return [{'unit_id': unit.id, 'role': role}]
