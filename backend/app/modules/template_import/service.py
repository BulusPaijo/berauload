"""Dry-run plan and atomic insertion; no existing reading is ever updated."""
from collections import defaultdict
from datetime import datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from ...catalog import CODE_MAP, calculate
from ...db import Metric, Reading, HourRecord, ImportBatch, AuditLog
from ..formulas.service import calculate_custom
from ..records.entry import formula_plan as formula_plan_for_unit
from ..unit_references.recalculation import recalculate
from ..org_units.repository import home_unit
from .repository import existing_values, statuses, imported_already

WITA = ZoneInfo('Asia/Makassar')
POWER_KEYS = {'pltu_lati_cb33_kw','pltu_lati_cb31_kw','sewa_tama_1_kw',
              'sewa_tama_2_kw','pltd_kw','pltu_berau_og3_kw','pltu_berau_og4_kw',
              'beban_suaran_kw','pltd_berau_kw','incoming_gi_kw'}
MODES = {'fill_empty', 'new_hours'}


def plan(db, unit_id, parsed, mode):
    if mode not in MODES:
        raise ValueError('Mode import tidak dikenal')
    existing = existing_values(db, unit_id, parsed['start'], parsed['end'])
    states = statuses(db, unit_id, parsed['start'], parsed['end'])
    counters = defaultdict(lambda: defaultdict(int))
    actions, differences = {}, []
    totals = defaultdict(int)
    for (day, hour), values in sorted(parsed['rows'].items()):
        locked = states.get(day, 'draft') != 'draft'
        old = existing.get((day,hour), {})
        hour_exists = bool(old)
        for code, value in values.items():
            if locked:
                category = 'locked'
            elif mode == 'new_hours' and hour_exists:
                category = 'skipped_hour'
            elif code not in old:
                category = 'inserted'
                actions.setdefault((day, hour), {})[code] = value
            elif Decimal(str(old[code])) == value:
                category = 'same'
            else:
                category = 'different'
                if len(differences) < 200:
                    differences.append({'day': day.isoformat(), 'hour': hour,
                                        'code': code, 'existing': str(old[code]),
                                        'uploaded': str(value)})
            counters[code][category] += 1
            totals[category] += 1
    summary = [{ 'code': code, **{name: counts.get(name, 0) for name in
                  ('inserted','same','different','locked','skipped_hour')}}
               for code, counts in sorted(counters.items())]
    return {'actions': actions, 'totals': dict(totals), 'by_parameter': summary,
            'differences': differences, 'hours_to_write': len(actions),
            'values_found': sum(len(v) for v in parsed['rows'].values())}


def computed_for_hour(db, unit_id, old, added, plan_formulas):
    """Mirror the PUT-hour calculation inputs; insert only missing results."""
    input_codes = {m.code for m in db.query(Metric).filter_by(input_mode='input',
                                                               active=True,unit_id=unit_id).all()}
    combined_inputs = {k: v for k, v in old.items() if k in input_codes}
    combined_inputs.update(added)
    source_only = {k: v for k, v in old.items()
                   if unit_id==home_unit(db).id and k in CODE_MAP and CODE_MAP[k][4] == 'imported'}
    changed_power = unit_id==home_unit(db).id and any(k in POWER_KEYS and old.get(k) != v
                        for k, v in added.items())
    built_in = calculate({k: v for k, v in {**source_only, **combined_inputs}.items()
                          if v is not None}) if changed_power else {}
    combined = {**combined_inputs, **built_in}
    for code, meta in CODE_MAP.items():
        if unit_id==home_unit(db).id and meta[4] == 'computed' and code not in built_in and code in old:
            combined[code] = old[code]
    custom, warnings = calculate_custom(db, {**old, **source_only, **combined},
                                        plan=plan_formulas)
    result = {**built_in, **custom}
    return {code: Decimal(str(value)) for code, value in result.items()
            if value is not None and code not in old}, warnings


def write(db, unit_id, parsed, mode, user, batch_id, filename, sha256):
    """The caller commits once. Any exception must roll back the whole session."""
    if imported_already(db, unit_id, sha256):
        raise FileExistsError('File identik sudah pernah diimport untuk unit ini')
    checked = plan(db, unit_id, parsed, mode)
    metrics = {m.code: m for m in db.query(Metric).filter_by(unit_id=unit_id).all()}
    old = existing_values(db, unit_id, parsed['start'], parsed['end'])
    formula_plan = formula_plan_for_unit(db, unit_id)
    inserted, computed_inserted, new_hours = 0, 0, 0
    batch = ImportBatch(id=batch_id, filename=filename, sha256=sha256,
                        unit_id=unit_id, kind='template', year=parsed['start'].year,
                        month=parsed['start'].month, created_by=user.id,
                        warnings=[])
    db.add(batch)
    for (day, hour), uploaded in sorted(checked['actions'].items()):
        previous = old.get((day,hour), {})
        if not previous:
            new_hours += 1
        slot = db.query(HourRecord).filter_by(day=day, hour=hour).first()
        if slot is None:
            moment = datetime.combine(day, time(hour=hour), tzinfo=WITA)
            slot = HourRecord(day=day, hour=hour,
                              timestamp_utc=moment.astimezone(timezone.utc),
                              entered_by=user.id)
            db.add(slot)
            db.flush()
        calculated, _ = computed_for_hour(db, unit_id, previous, uploaded, formula_plan)
        # A computed value cannot override an explicitly imported input.
        values = {**calculated, **uploaded}
        written_codes = set()
        for code, value in values.items():
            metric = metrics.get(code)
            if metric is None or code in previous:
                continue
            db.add(Reading(hour_id=slot.id, metric_id=metric.id,
                           value=Decimal(str(value)), source='template_import',
                           import_batch_id=batch_id))
            written_codes.add(code)
            inserted += 1
            if code not in uploaded:
                computed_inserted += 1
        # Recompute descendants' parents once after this hour's actual inserts.
        # The caller commits both the readings and the recaps in one transaction.
        if written_codes:
            recalculate(db, day, hour, unit_id, written_codes)
        old[(day,hour)] = {**previous, **values}
    batch.hours_created = new_hours
    batch.hours_skipped = max(0, len(parsed['rows']) - len(checked['actions']))
    batch.readings_created = inserted
    db.add(AuditLog(user_id=user.id, action='template_import_commit', target=batch_id,
                    detail={'unit_id': unit_id, 'actor_role': 'admin_global' if user.role=='admin' else 'operator', 'mode': mode, 'filename': filename,
                            'readings_created': inserted,
                            'computed_created': computed_inserted,
                            'counts': checked['totals']}))
    db.flush()
    return {'id': batch_id, 'kind': 'template', 'hours_created': new_hours,
            'hours_skipped': batch.hours_skipped, 'readings_created': inserted,
            'computed_created': computed_inserted,
            'counts': checked['totals']}
