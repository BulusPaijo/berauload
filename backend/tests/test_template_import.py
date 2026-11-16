"""V1.6.0 stage 2: synthetic SQLite and generated XLSX, no production access."""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import os
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault('ADMIN_PASSWORD', 'Test-Template-Password-123456')
from app.db import get_db, Asset, Metric, Reading, HourRecord, DayState, User, ImportBatch
from app.modules.org_units.models import UnitDayState
from app.modules.org_units.repository import home_unit
from app import main
from app.modules.template_import import router as tpl_router
from app.modules.template_import import migrations as tpl_migrate


@pytest.fixture
def server(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///'+str(tmp_path/'test.db'),
                           connect_args={'check_same_thread': False})
    session = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'SessionLocal', session)
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path/'uploads')
    monkeypatch.setattr(main, 'STAGING_DIR', tmp_path/'uploads'/'staging')
    monkeypatch.setattr(tpl_router, 'UPLOAD_DIR', tmp_path/'uploads')
    monkeypatch.setattr(tpl_router, 'STAGING', tmp_path/'uploads'/'staging'/'template_import')
    monkeypatch.setenv('ADMIN_PASSWORD', 'Test-Template-Password-123456')

    def override():
        with session() as db:
            yield db
    main.app.dependency_overrides[get_db] = override
    try:
        with TestClient(main.app) as client:
            login = client.post('/api/auth/login', json={
                'username': 'admin', 'password': 'Test-Template-Password-123456'})
            assert login.status_code == 200, login.text
            headers = {'X-CSRF-Token': login.json()['csrf']}
            yield client, session, headers, tmp_path
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def template(client, start='2026-11-10', end='2026-11-10', tabs='PEMBANGKIT'):
    resp = client.get('/api/template-import/template', params={
        'start': start, 'end': end, 'tabs': tabs})
    assert resp.status_code == 200, resp.text
    return resp.content


def edited(raw, setter):
    wb = load_workbook(BytesIO(raw))
    sheet = next(s for s in wb if s.title not in ('Petunjuk', '_meta'))
    sheet.protection.sheet = False
    setter(wb, sheet)
    out = BytesIO()
    wb.save(out)
    wb.close()
    return out.getvalue()


def preview(client, headers, raw, mode='fill_empty', filename='work.xlsx'):
    return client.post('/api/template-import/preview', headers=headers,
                       data={'mode': mode},
                       files={'file': (filename, raw, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})


def commit(client, headers, token):
    return client.post('/api/template-import/commit', headers=headers,
                       json={'token': token})


def filled(raw, a=0, b=4):
    return edited(raw, lambda wb, s: (setattr(s['C4'], 'value', a),
                                       setattr(s['D4'], 'value', b)))


def test_template_rows_metadata_and_visible_input_only(server):
    client, session, headers, tmp = server
    raw = template(client, '2026-11-10', '2026-11-11')
    book = load_workbook(BytesIO(raw))
    assert book.sheetnames == ['Petunjuk', 'Pembangkit', '_meta']
    assert book['_meta'].sheet_state == 'hidden'
    assert book['_meta']['B1'].value == 'berauload_hourly'
    assert book['_meta']['B3'].value == 'ulp_tanjung_redeb'
    sheet = book['Pembangkit']
    assert sheet.max_row == 3+48
    assert sheet.freeze_panes == 'C4'
    assert sheet['A4'].value == '2026-11-10' and sheet['B4'].value == 0
    assert sheet['C3'].value == 'pltu_lati_cb33_kw'
    assert sheet['C1'].value == 'PLTU Lati CB-33'
    assert sheet['C2'].value == 'kW'
    assert sheet['C4'].protection.locked is False
    assert sheet['B4'].protection.locked is True
    assert 'beban_sistem_kw' not in [cell.value for cell in sheet[3]]
    assert 'daya_mampu_sistem_kw' not in [cell.value for cell in sheet[3]]
    assert 'tambang_lati_kw' not in [cell.value for cell in sheet[3]]
    book.close()
    assert preview(client, headers, raw).status_code == 200
    result = preview(client, headers, raw).json()
    assert result['values_found'] == 0 and result['hours_to_write'] == 0
    done = commit(client, headers, result['token'])
    assert done.status_code == 200, done.text
    assert done.json()['readings_created'] == 0
    with session() as db:
        assert db.query(Reading).count() == 0


def test_zero_empty_mapping_renamed_header_and_reordered_columns(server):
    client, session, headers, tmp = server
    raw = template(client)
    def change(wb, ws):
        ws['C1'] = 'Judul telah berubah';ws['D1'] = 'Name changed'
        original = ws['C3'].value
        ws['C3'], ws['D3'] = ws['D3'].value, original
        ws['C4'], ws['D4'] = 15, 0
    modified = edited(raw, change)
    check = preview(client, headers, modified)
    assert check.status_code == 200, check.text
    done = commit(client, headers, check.json()['token'])
    assert done.status_code == 200, done.text
    with session() as db:
        values = {m.code: Decimal(str(r.value)) for r,m in db.query(Reading, Metric).join(
            Metric, Metric.id==Reading.metric_id).all()}
        assert values['pltu_lati_cb33_kw'] == 0
        assert values['pltu_lati_cb31_kw'] == 15
        assert values['jumlah_beban_kw'] == 15
        assert all(r.source == 'template_import' for r in db.query(Reading).all())
        assert len(db.query(HourRecord).all()) == 1


@pytest.mark.parametrize('case,cell', [
    ('unknown','C3'), ('text','C4'), ('formula','C4'),
    ('bool','C4'), ('hour','B4'), ('date','A4'),
    ('duplicate_row','B5'), ('wrong_unit','B1'), ('no_meta','A1'),
    ('duplicate_code','D3'), ('infinite','C4'), ('header_formula','C1')
])
def test_invalid_excel_is_atomic_and_located(server, case, cell):
    client, session, headers, tmp = server
    def corrupt(book, sheet):
        if case == 'unknown':sheet['C3'] = 'unknown_bad'
        if case == 'text':sheet['C4'] = 'teks'
        if case == 'formula':sheet['C4'] = '=1+1'
        if case == 'bool':sheet['C4'] = True
        if case == 'hour':sheet['B4'] = 24
        if case == 'date':sheet['A4'] = '2026-10-01'
        if case == 'duplicate_row':sheet['A5'], sheet['B5'] = sheet['A4'].value, sheet['B4'].value
        if case == 'wrong_unit':book['_meta']['B3'] = 'ulp_lain'
        if case == 'no_meta':del book['_meta']
        if case == 'duplicate_code':sheet['D3'] = sheet['C3'].value
        if case == 'infinite':sheet['C4'] = 'NaN'
        if case == 'header_formula':sheet['C1'] = '=HYPERLINK("https://evil.invalid","ok")'
    content = edited(template(client), corrupt)
    result = preview(client, headers, content)
    assert result.status_code == 422, (case, result.text)
    errors = result.json()['detail']['errors']
    assert errors and any(x['cell'] == cell for x in errors), (case, errors)
    with session() as db:
        assert db.query(Reading).count() == 0
        assert db.query(HourRecord).count() == 0


def test_fill_empty_no_overwrite_duplicate_file_and_lock(server):
    client, session, headers, tmp = server
    original = filled(template(client), 0, 4)
    first = preview(client, headers, original).json()
    assert commit(client, headers, first['token']).status_code == 200
    assert preview(client, headers, original).status_code == 409
    different = filled(template(client), 20, 4)
    dry = preview(client, headers, different)
    assert dry.status_code == 200, dry.text
    assert dry.json()['counts']['different'] == 1
    assert dry.json()['counts']['same'] == 1
    assert len(dry.json()['differences']) == 1
    assert commit(client, headers, dry.json()['token']).status_code == 200
    with session() as db:
        saved = db.query(Reading).join(Metric).filter(Metric.code=='pltu_lati_cb33_kw').one()
        assert saved.value == Decimal('0')
        # Final state is protected, including an otherwise-empty cell.
        db.add(UnitDayState(day=date(2026,11,10), unit_id=home_unit(db).id, status='final'))
        db.commit()
    another = filled(template(client), 0, 6)
    last = preview(client, headers, another).json()
    assert last['counts']['locked'] == 2
    assert commit(client, headers, last['token']).status_code == 200
    with session() as db:
        assert db.query(Reading).count() == 3


def test_new_hours_existing_unit_vs_global_and_computed_not_overwritten(server):
    client, session, headers, tmp = server
    with session() as db:
        # Existing global slot from another unit: should not block unit home.
        from app.modules.org_units.models import OrgUnit
        root = db.query(OrgUnit).filter_by(level='up3').one()
        ulp = OrgUnit(code='ulp_qa',name='ULP Test',level='ulp',parent_id=root.id)
        db.add(ulp);db.flush()
        metric = Metric(code='qa_only', name='QA', unit='kW', group_name='REKAP',
                        input_mode='input', unit_id=ulp.id, active=True)
        db.add(metric);db.flush()
        slot=HourRecord(day=date(2026,11,10),hour=0,
                        timestamp_utc=datetime(2026,11,9,16,tzinfo=timezone.utc))
        db.add(slot);db.flush()
        db.add(Reading(hour_id=slot.id,metric_id=metric.id,value=Decimal('123'),source='manual'))
        db.commit()
    raw = filled(template(client), 0, 4)
    check = preview(client, headers, raw, 'new_hours')
    assert check.status_code == 200 and check.json()['hours_to_write'] == 1
    assert commit(client, headers, check.json()['token']).status_code == 200
    more = filled(template(client), 2, 8)
    check = preview(client, headers, more, 'new_hours').json()
    assert check['counts']['skipped_hour'] == 2
    assert commit(client, headers, check['token']).status_code == 200
    with session() as db:
        assert db.query(Reading).join(Metric).filter(Metric.code=='qa_only').one().value == 123
        assert db.query(HourRecord).count() == 1
        computed=db.query(Reading).join(Metric).filter(Metric.code=='jumlah_beban_kw').one()
        assert computed.value==Decimal('4')


def test_permission_csrf_rollback_and_migration_idempotent(server, monkeypatch):
    client, session, headers, tmp = server
    contents = filled(template(client), 5, 3)
    assert preview(client, {}, contents).status_code == 403
    assert preview(client, {'X-CSRF-Token':'wrong'}, contents).status_code == 403
    bad=preview(client, headers, contents)
    assert bad.status_code==200
    from app.modules.template_import import service
    def broken(*args, **kwargs):
        raise RuntimeError('forced error while computing')
    with monkeypatch.context() as mp:
        mp.setattr(service, 'computed_for_hour', broken)
        with pytest.raises(RuntimeError):
            commit(client, headers, bad.json()['token'])
    with session() as db:
        assert db.query(Reading).count() == 0
        assert db.query(HourRecord).count() == 0
        assert db.query(ImportBatch).count() == 0
    with session() as db:
        db.add(ImportBatch(id='legacy',filename='legacy.xlsx',sha256='old',
                           year=2026,month=11,unit_id=home_unit(db).id))
        db.commit()
    tpl_migrate.run(main.engine)
    tpl_migrate.run(main.engine)
    with session() as db:
        assert db.query(ImportBatch).filter_by(id='legacy').one().kind=='legacy_excel'
        assert db.query(ImportBatch).count() == 1
    history = client.get('/api/template-import/history')
    assert history.status_code == 200
    assert history.json()[0]['kind'] == 'legacy_excel'


def test_computed_existing_not_overwritten_when_new_input_inserted(server):
    client, session, headers, tmp = server
    with session() as db:
        computed = db.query(Metric).filter_by(code='jumlah_beban_kw').one()
        old_input = db.query(Metric).filter_by(code='pltu_lati_cb33_kw').one()
        slot = HourRecord(day=date(2026,11,10),hour=0,
                          timestamp_utc=datetime(2026,11,9,16,tzinfo=timezone.utc))
        db.add(slot);db.flush()
        db.add_all([Reading(hour_id=slot.id,metric_id=computed.id,
                            value=Decimal('999'),source='excel_import'),
                    Reading(hour_id=slot.id,metric_id=old_input.id,
                            value=Decimal('10'),source='manual')])
        db.commit()
    content = filled(template(client), 10, 3)
    dry = preview(client, headers, content).json()
    assert dry['counts']['same'] == 1 and dry['counts']['inserted'] == 1
    assert commit(client, headers, dry['token']).status_code == 200
    with session() as db:
        old = db.query(Reading).join(Metric).filter(Metric.code=='jumlah_beban_kw').one()
        assert old.value == Decimal('999') and old.source == 'excel_import'
        new = db.query(Reading).join(Metric).filter(Metric.code=='pltu_lati_cb31_kw').one()
        assert new.value == Decimal('3') and new.source == 'template_import'


def test_hidden_tab_and_inactive_metrics_never_exported(server):
    client, session, headers, tmp = server
    from app.modules.input_forms.models import InputFormPlacement,InputFormTab
    with session() as db:
        placement = db.query(InputFormPlacement).filter_by(metric_code='pltu_lati_cb33_kw').first()
        if placement is None:
            placement = InputFormPlacement(unit_id=db.query(Metric).filter_by(code='pltu_lati_cb33_kw').one().unit_id,
                                       metric_code='pltu_lati_cb33_kw',
                        tab_code='PEMBANGKIT', visible=False)
            db.add(placement)
        else:
            placement.visible = False
        metric = db.query(Metric).filter_by(code='pltu_lati_cb31_kw').one()
        metric.active = False
        db.commit()
    result = template(client)
    wb = load_workbook(BytesIO(result))
    codes = [c.value for c in wb['Pembangkit'][3]]
    assert 'pltu_lati_cb33_kw' not in codes
    assert 'pltu_lati_cb31_kw' not in codes
    wb.close()


def test_legacy_import_endpoint_and_role_policy_unchanged(server):
    client, session, headers, tmp = server
    with session() as db:
        admin = db.query(User).filter_by(username='admin').one()
        from app.security import hash_password
        from app.modules.org_units.repository import attach_new_user
        manager = User(username='mgr', display_name='Manager',
                       password_hash=hash_password('Management-Pass-123456'),
                       role='management',active=True)
        db.add(manager);attach_new_user(db,manager);db.commit()
    legacy = client.get('/api/imports')
    assert legacy.status_code == 200 and isinstance(legacy.json(),list)
    client.post('/api/auth/logout', headers=headers)
    login = client.post('/api/auth/login', json={
        'username':'mgr','password':'Management-Pass-123456'})
    assert login.status_code == 200
    manager_headers={'X-CSRF-Token':login.json()['csrf']}
    assert client.get('/api/template-import/config').status_code == 200
    assert client.get('/api/template-import/template',params={
        'start':'2026-11-10','end':'2026-11-10'}).status_code == 403
    assert preview(client, manager_headers, b'bad').status_code == 403
    assert client.get('/api/template-import/history').status_code == 200


def test_migration_from_pre_kind_schema_runs_only_once(tmp_path):
    engine = create_engine('sqlite:///'+str(tmp_path/'old.db'))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE import_batches (id TEXT PRIMARY KEY, filename TEXT, "
                          "sha256 TEXT, year INTEGER, month INTEGER, unit_id INTEGER)"))
        conn.execute(text("INSERT INTO import_batches VALUES "
                          "('old-1','one.xlsx','same',2026,11,2),"
                          "('old-2','two.xlsx','same',2026,11,2)"))
    tpl_migrate.run(engine)
    with engine.connect() as conn:
        expected = conn.execute(text('SELECT id,kind FROM import_batches ORDER BY id')).all()
        versions = conn.execute(text("SELECT count(*) FROM schema_migrations WHERE "
                                     "version='20261115_13_template_import_batch_kind'")).scalar()
    tpl_migrate.run(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id,kind FROM import_batches ORDER BY id')).all() == expected
        assert conn.execute(text("SELECT count(*) FROM schema_migrations WHERE "
                                 "version='20261115_13_template_import_batch_kind'")).scalar() == versions == 1
    assert expected == [('old-1','legacy_excel'),('old-2','legacy_excel')]
    engine.dispose()


def test_custom_formula_insert_matches_manual_engine(server):
    client, session, headers, tmp = server
    response=client.post('/api/formulas',headers=headers,json={
        'code':'qa_total_lati','name':'Total Lati QA','unit':'kW',
        'expression':'pltu_lati_cb33_kw + pltu_lati_cb31_kw',
        'group_name':'REKAP'})
    assert response.status_code == 201, response.text
    raw = filled(template(client), 7, 8)
    dry = preview(client, headers, raw)
    assert dry.status_code == 200, dry.text
    done = commit(client, headers, dry.json()['token'])
    assert done.status_code == 200, done.text
    with session() as db:
        formula = db.query(Reading).join(Metric).filter(Metric.code=='qa_total_lati').one()
        assert formula.value == Decimal('15')
        assert formula.source == 'template_import'
        assert db.query(ImportBatch).one().kind == 'template'
    assert (tmp/'uploads'/(done.json()['id']+'.xlsx')).is_file()


def test_duplicate_metric_across_sheets_and_date_window_limit(server):
    client, session, headers, tmp = server
    assert client.get('/api/template-import/template',params={
        'start':'2026-01-01','end':'2026-04-03'}).status_code == 422
    raw = template(client,tabs='PEMBANGKIT,KUALITAS')
    def change(wb, first):
        other=next(s for s in wb if s.title not in ('Petunjuk','_meta',first.title))
        other['C3'] = first['C3'].value
    candidate = edited(raw,change)
    result = preview(client, headers, candidate)
    assert result.status_code==422
    assert any(x['message']=='Kode parameter ganda antar-sheet'
               for x in result.json()['detail']['errors'])
