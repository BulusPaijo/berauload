"""Stage 5 template import recaps: synthetic SQLite and isolated file archives."""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from test_stage4a_units import as_unit, site
from app.db import AuditLog, HourRecord, ImportBatch, Metric, Reading
from app.modules.org_units.models import UnitDayState
from app.modules.input_forms.models import InputFormTab, InputFormPlacement
from app.modules.template_import import router as template_router
from app.modules.template_import import service as template_service
from app.modules.unit_references.models import UnitSourceChange


@pytest.fixture
def import_site(site, tmp_path, monkeypatch):
    monkeypatch.setattr(template_router, 'UPLOAD_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(template_router, 'STAGING', tmp_path / 'uploads' / 'staging' / 'template')
    _, Session, _, ids = site
    with Session() as db:
        db.add(InputFormTab(code='TEST_KP_INPUT', name='Input KP',
                            unit_id=ids['kp'], active=True))
        db.add(InputFormPlacement(metric_code='kp_load', tab_code='TEST_KP_INPUT',
                                  unit_id=ids['kp'], visible=True))
        db.commit()
    return (*site, tmp_path)


def make_formula(client, headers, unit, code, expression):
    result = client.post('/api/formulas', headers=as_unit(headers, unit), json={
        'code': code, 'name': code, 'unit': 'kW', 'group_name': 'REKAP',
        'expression': expression})
    assert result.status_code == 201, result.text


def make_template(client, headers, unit, values, day='2026-11-12'):
    unit_headers = as_unit(headers, unit)
    response = client.get('/api/template-import/template', headers=unit_headers,
                          params={'start': day, 'end': day})
    assert response.status_code == 200, response.text
    wb = load_workbook(BytesIO(response.content))
    sheet = next(tab for tab in wb if tab.title not in ('Petunjuk', '_meta'))
    assert sheet['C3'].value == 'kp_load'
    for index, value in enumerate(values, 4):
        sheet[f'C{index}'] = value
    output = BytesIO()
    wb.save(output)
    wb.close()
    return output.getvalue()


def import_values(client, headers, unit, contents):
    head = as_unit(headers, unit)
    staged = client.post('/api/template-import/preview', headers=head,
                         data={'mode': 'fill_empty'},
                         files={'file': ('kp.xlsx', contents,
                                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert staged.status_code == 200, staged.text
    return client.post('/api/template-import/commit', headers=head,
                       json={'token': staged.json()['token']})


def reading(Session, code, day='2026-11-12', hour=0):
    with Session() as db:
        row = (db.query(Reading).join(Metric, Reading.metric_id == Metric.id)
               .join(HourRecord, Reading.hour_id == HourRecord.id)
               .filter(Metric.code == code, HourRecord.day == date.fromisoformat(day),
                       HourRecord.hour == hour).one_or_none())
        return row


def test_import_kp_computed_source_recalculates_ulp_and_up3_once(import_site, monkeypatch):
    client, Session, headers, ids, _ = import_site
    make_formula(client, headers, ids['kp'], 'kp_local_kw', 'kp_load + 1')
    make_formula(client, headers, ids['other'], 'ulp_template_kw', 'kp_local_kw + 2')
    make_formula(client, headers, ids['root'], 'up3_template_kw', 'ulp_template_kw + 3')
    calls = []
    actual = template_service.recalculate

    def tracked(db, day, hour, source_id, codes):
        calls.append((day, hour, source_id, set(codes)))
        return actual(db, day, hour, source_id, codes)

    monkeypatch.setattr(template_service, 'recalculate', tracked)
    result = import_values(client, headers, ids['kp'], make_template(client, headers,
                                                                      ids['kp'], [0]))
    assert result.status_code == 200, result.text
    assert len(calls) == 1
    assert calls[0][2] == ids['kp']
    assert calls[0][3] == {'kp_load', 'kp_local_kw'}
    assert result.json()['readings_created'] == 2
    assert reading(Session, 'kp_load').value == 0
    assert reading(Session, 'kp_local_kw').value == 1
    assert reading(Session, 'ulp_template_kw').value == 3
    assert reading(Session, 'up3_template_kw').value == 6


def test_import_missing_operand_returns_null_not_partial(import_site):
    client, Session, headers, ids, _ = import_site
    make_formula(client, headers, ids['other'], 'ulp_incomplete_kw',
                 'SUM(kp_load, other_load)')
    make_formula(client, headers, ids['root'], 'up3_incomplete_kw',
                 'ulp_incomplete_kw + 1')
    result = import_values(client, headers, ids['kp'], make_template(client, headers,
                                                                      ids['kp'], [4]))
    assert result.status_code == 200, result.text
    assert reading(Session, 'kp_load').value == 4
    assert reading(Session, 'ulp_incomplete_kw') is None
    assert reading(Session, 'up3_incomplete_kw') is None
    response = client.get('/api/formulas/completeness?day=2026-11-12&hour=0',
                          headers=as_unit(headers, ids['other']))
    assert response.status_code == 200, response.text
    assert '1 dari 2 sumber terisi' in [f['label'] for f in response.json()['formulas']]


def test_import_keeps_final_ulp_snapshot_and_flags_change(import_site):
    client, Session, headers, ids, _ = import_site
    make_formula(client, headers, ids['other'], 'ulp_locked_kw', 'kp_load + 1')
    make_formula(client, headers, ids['root'], 'up3_live_kw', 'kp_load + 2')
    with Session() as db:
        target = db.query(Metric).filter_by(code='ulp_locked_kw').one()
        slot = HourRecord(day=date(2026, 11, 12), hour=0,
                          timestamp_utc=datetime(2026, 11, 11, 16,
                                                 tzinfo=timezone.utc))
        db.add(slot)
        db.flush()
        db.add(Reading(hour_id=slot.id, metric_id=target.id,
                       value=Decimal('77'), source='computed'))
        db.add(UnitDayState(unit_id=ids['other'], day=date(2026, 11, 12),
                            status='final'))
        db.commit()
    response = import_values(client, headers, ids['kp'], make_template(client, headers,
                                                                       ids['kp'], [6]))
    assert response.status_code == 200, response.text
    assert reading(Session, 'ulp_locked_kw').value == 77
    assert reading(Session, 'up3_live_kw').value == 8
    with Session() as db:
        flags = db.query(UnitSourceChange).filter_by(unit_id=ids['other'],
                          source_unit_id=ids['kp']).all()
        assert len(flags) == 1
        assert db.query(AuditLog).filter_by(action='source_changed_after_final').count() == 1
    status = client.get('/api/days/2026-11-12/status',
                        headers=as_unit(headers, ids['other']))
    assert status.status_code == 200
    assert status.json()['source_changed_after_final'] is True


def test_recalculation_failure_rolls_back_batch_readings_and_archive(import_site, monkeypatch):
    client, Session, headers, ids, tmp_path = import_site
    make_formula(client, headers, ids['other'], 'ulp_atomic_kw', 'kp_load + 1')
    make_formula(client, headers, ids['root'], 'up3_atomic_kw', 'ulp_atomic_kw + 1')
    contents = make_template(client, headers, ids['kp'], [3, 4])
    head = as_unit(headers, ids['kp'])
    staged = client.post('/api/template-import/preview', headers=head,
                         data={'mode':'fill_empty'},
                         files={'file':('kp.xlsx', contents,
                                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert staged.status_code == 200, staged.text
    actual = template_service.recalculate
    attempts = 0

    def fail_on_second(db, day, hour, source_id, codes):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise RuntimeError('forced recap failure')
        return actual(db, day, hour, source_id, codes)

    monkeypatch.setattr(template_service, 'recalculate', fail_on_second)
    with pytest.raises(RuntimeError, match='forced recap failure'):
        client.post('/api/template-import/commit', headers=head,
                    json={'token':staged.json()['token']})
    assert attempts == 2
    with Session() as db:
        assert db.query(ImportBatch).count() == 0
        assert db.query(HourRecord).count() == 0
        assert db.query(Reading).count() == 0
        assert db.query(UnitSourceChange).count() == 0
        assert db.query(AuditLog).filter_by(action='template_import_commit').count() == 0
    assert list((tmp_path/'uploads').glob('*.xlsx')) == []
    assert (template_router.STAGING / (staged.json()['token']+'.xlsx')).exists()


def test_final_kp_day_is_skipped_with_no_recalculation(import_site, monkeypatch):
    client, Session, headers, ids, _ = import_site
    with Session() as db:
        db.add(UnitDayState(unit_id=ids['kp'], day=date(2026, 11, 12), status='verified'))
        db.commit()
    def forbidden(*args, **kwargs):
        raise AssertionError('No recalculation allowed for locked KP day')
    monkeypatch.setattr(template_service, 'recalculate', forbidden)
    response = import_values(client, headers, ids['kp'], make_template(client, headers,
                                                                       ids['kp'], [2]))
    assert response.status_code == 200, response.text
    assert response.json()['readings_created'] == 0
    assert reading(Session, 'kp_load') is None
