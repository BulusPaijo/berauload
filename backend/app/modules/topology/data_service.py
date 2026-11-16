"""Read-only DTO assembly using the existing Engineering Rule evaluator."""
from datetime import date
from ..engineering.service import evaluate_sample
from ..formulas.engine import FormulaError, parse_formula
from ..units.models import UnitDefinition
from ..units.service import profile
from .repository import read_day, read_hour, day_status


def requested_codes(layout):
    return {code for box in layout['boxes'] for code in box['metric_codes']}


def requested_rules(layout, rules):
    return {rid: rules[rid] for rid in {box['rule_id'] for box in layout['boxes']}
            if rid is not None and rid in rules}


def rule_codes(rules):
    codes = set()
    for rule in rules.values():
        try:
            codes.update(parse_formula(rule.expression)[1])
        except FormulaError:
            continue
    return codes


def rule_result(rule, values, units, unit_registry, day):
    if day < rule.effective_from:
        return None
    spec = {name: getattr(rule, name) for name in (
        'expression', 'unit', 'direction', 'warning_threshold', 'critical_threshold')}
    result = evaluate_sample(spec, values, units, unit_registry)
    return result['status'] if result['status'] in {'normal', 'warning', 'critical'} else None


def hourly_data(db, layout, day: date, hour: int, metrics, rules, unit_id):
    codes = requested_codes(layout)
    all_rule_ids = {b['rule_id'] for b in layout['boxes'] if b['rule_id'] is not None}
    applicable = requested_rules(layout, rules)
    inputs = codes | rule_codes(applicable)
    readings = read_hour(db, day, hour, inputs, unit_id)  # one SELECT for all necessary measurements
    units = {code: metrics[code][0] for code in codes if code in metrics}
    eval_units = {code: details[0] for code, details in metrics.items()}
    registry = profile(db.query(UnitDefinition).all())
    result = {rid: (rule_result(applicable[rid], readings, eval_units, registry, day)
                    if rid in applicable else None) for rid in all_rule_ids}
    return {'day': day.isoformat(), 'hour': hour, 'day_status': day_status(db, day, unit_id),
            'values': {code: readings.get(code) for code in sorted(codes)},
            'units': units, 'rules': result}


def day_series(db, layout, day: date, metrics, unit_id):
    codes = requested_codes(layout)
    rows = read_day(db, day, codes, unit_id)
    return {'day': day.isoformat(), 'day_status': day_status(db, day, unit_id),
            'units': {code: metrics[code][0] for code in codes if code in metrics},
            'series': {code: [{'hour': hour, 'value': rows.get((hour, code))}
                               for hour in range(24)] for code in sorted(codes)}}
