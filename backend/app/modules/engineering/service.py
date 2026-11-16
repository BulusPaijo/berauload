"""Pure deterministic threshold evaluation and read-only historic aggregation."""
from __future__ import annotations
from collections import Counter
from datetime import date
from math import isfinite
from typing import Iterable
from ..formulas.engine import FormulaError, MissingValue, evaluate, validate, parse_formula
from ..units.formula import validate_units, evaluate_units

RULE_FIELDS = ('code', 'name', 'expression', 'unit', 'direction',
               'warning_threshold', 'critical_threshold', 'reference_note', 'effective_from')


def validate_rule(spec: dict, units: dict[str, str], registry=None) -> frozenset[str]:
    direction = spec['direction']
    warning = float(spec['warning_threshold'])
    critical = float(spec['critical_threshold'])
    if not all(isfinite(x) and abs(x) <= 1e12 for x in (warning, critical)):
        raise FormulaError('Ambang batas harus angka terbatas')
    if direction == 'below' and not critical < warning:
        raise FormulaError('Untuk batas bawah: nilai kritis harus lebih kecil dari waspada')
    if direction == 'above' and not critical > warning:
        raise FormulaError('Untuk batas atas: nilai kritis harus lebih besar dari waspada')
    if direction not in {'below', 'above'}:
        raise FormulaError('Arah ambang tidak dikenal')
    if spec['effective_from'].year < 2000 or spec['effective_from'].year > 2100:
        raise FormulaError('Tanggal berlaku tidak valid')
    return (validate_units(spec['expression'], spec['unit'], units, registry)
            if registry else validate(spec['expression'], spec['unit'], units)).variables


def classify(value: float | None, direction: str, warning: float, critical: float) -> str:
    if value is None or not isfinite(value):
        return 'no_data'
    if direction == 'below':
        if value <= critical: return 'critical'
        if value <= warning: return 'warning'
    else:
        if value >= critical: return 'critical'
        if value >= warning: return 'warning'
    return 'normal'


def evaluate_sample(spec: dict, samples: dict[str, float], source_units=None, registry=None):
    try:
        convert_needed = bool(registry and source_units and any(
            source_units.get(ref) != spec['unit'] for ref in parse_formula(spec['expression'])[1]))
        value = (evaluate_units(spec['expression'], samples, spec['unit'], source_units, registry)
                 if convert_needed else evaluate(spec['expression'], samples))
    except MissingValue as exc:
        return {'value': None, 'status': 'no_data', 'missing': sorted(exc.names)}
    except FormulaError as exc:
        return {'value': None, 'status': 'invalid', 'reason': str(exc)}
    return {'value': value, 'status': classify(value, spec['direction'],
            spec['warning_threshold'], spec['critical_threshold']), 'missing': []}


def evaluate_history(spec: dict, rows: Iterable[tuple], start: date, end: date, source_units=None, registry=None):
    """Process observed hour buckets; missing hours are counted but never assumed normal."""
    expected = ((end - start).days + 1) * 24
    counts = Counter()
    events = []
    day_counts: dict[str, Counter] = {}
    last = None
    values: dict[str, float] = {}

    def finish():
        if last is None: return
        day, hour = last
        data = evaluate_sample(spec, values, source_units, registry)
        status = data['status']
        counts[status] += 1
        by_day = day_counts.setdefault(day.isoformat(), Counter())
        by_day[status] += 1
        if status in {'warning', 'critical'} and len(events) < 500:
            events.append({'day': day.isoformat(), 'hour': hour,
                           'value': data['value'], 'status': status})

    for day, hour, code, value in rows:
        key = (day, hour)
        if key != last:
            finish()
            last, values = key, {}
        values[code] = float(value)
    finish()
    valid = counts['normal'] + counts['warning'] + counts['critical']
    missing = max(0, expected - valid)
    return {'expected_hours': expected, 'valid_hours': valid,
            'coverage_pct': round(valid / expected * 100, 2),
            'status_counts': {s: counts[s] for s in ('normal', 'warning', 'critical')},
            'missing_or_invalid_hours': missing,
            'observed_invalid_hours': counts['no_data'] + counts['invalid'],
            'events': events, 'events_capped': counts['warning'] + counts['critical'] > 500,
            'by_day': [{'day': day, **{s: count[s] for s in ('normal', 'warning', 'critical', 'no_data', 'invalid')}}
                       for day, count in sorted(day_counts.items())],
            'advisory_only': True}
