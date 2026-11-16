"""Validation and dependency resolution are separate from HTTP and SQL persistence."""
from __future__ import annotations
import logging
from .engine import FormulaError, MissingValue, evaluate, parse_formula, validate
from .repository import list_formulas, list_metrics
from ..units.models import UnitDefinition
from ..units.service import profile
from ..units.formula import validate_units, evaluate_units


def validate_candidate(db, code: str, unit: str, expression: str):
    metrics = list_metrics(db)
    by_code = {m.code: m for m in metrics}
    if code in by_code:
        raise FormulaError('Kode parameter sudah digunakan')
    available = {m.code: m.unit for m in metrics if m.active}
    registry = profile(db.query(UnitDefinition).filter_by(active=True).all())
    spec = validate_units(expression, unit, available, registry)
    return spec


def dependency_order(definitions):
    """Return formula rows in dependency order; reject circular references."""
    refs = {m.code: parse_formula(d.expression)[1] for d, m in definitions}
    rows = {m.code: (d, m) for d, m in definitions}
    visiting: set[str] = set()
    visited: set[str] = set()
    result = []

    def visit(code):
        if code in visiting:
            raise FormulaError('Terdapat ketergantungan rumus melingkar')
        if code in visited:
            return
        visiting.add(code)
        for ref in refs[code]:
            if ref in rows:
                visit(ref)
        visiting.remove(code)
        visited.add(code)
        result.append(rows[code])

    for code in rows:
        visit(code)
    return result


def active_plan(db):
    """Prepare dependency graph once, e.g. before a large bulk import."""
    return dependency_order([(d, m) for d, m in list_formulas(db) if m.active])


def calculate_custom(db, source: dict[str, float], plan=None) -> tuple[dict[str, float | None], dict[str, str]]:
    """Compute current active formulas only; no rewriting existing historical hours."""
    order = plan if plan is not None else active_plan(db)
    if not order:
        return {}, {}
    custom_codes = {m.code for _, m in order}
    if '_units_profile' not in db.info:
        db.info['_units_profile'] = profile(db.query(UnitDefinition).all())
    if '_metric_units' not in db.info:
        db.info['_metric_units'] = {m.code: m.unit for m in list_metrics(db)}
    registry = db.info['_units_profile']
    units = db.info['_metric_units']
    available = {k: v for k, v in source.items() if k not in custom_codes and v is not None}
    calculated: dict[str, float | None] = {}
    warnings: dict[str, str] = {}
    for definition, metric in order:
        try:
            refs = parse_formula(definition.expression)[1]
            # Legacy same-unit formulas keep the V1.1 evaluator unchanged.
            if all(units.get(ref) == metric.unit for ref in refs):
                result = evaluate(definition.expression, available)
            else:
                result = evaluate_units(definition.expression, available, metric.unit,
                                        units, registry)
            available[metric.code] = result
            calculated[metric.code] = result
        except (FormulaError, MissingValue) as exc:
            calculated[metric.code] = None
            warnings[metric.code] = str(exc)
            if not isinstance(exc, MissingValue):
                logging.getLogger("berauload.formulas").warning(
                    "Formula %s tidak dapat dihitung: %s", metric.code, exc)
    return calculated, warnings


def preview(expression: str, unit: str, values: dict[str, float | None],
            units: dict[str, str], registry=None):
    spec = validate_units(expression, unit, units, registry) if registry else validate(expression, unit, units)
    sample = {k: v for k, v in values.items() if v is not None}
    try:
        return {'valid': True, 'result': (evaluate_units(expression, sample, unit, units, registry)
                            if registry and any(units.get(ref) != unit for ref in spec.variables)
                            else evaluate(expression, sample)),
                'missing': [], 'references': sorted(spec.variables)}
    except MissingValue as exc:
        return {'valid': True, 'result': None,
                'missing': sorted(exc.names), 'references': sorted(spec.variables)}
    except FormulaError as exc:
        return {'valid': True, 'result': None, 'missing': [],
                'warning': str(exc), 'references': sorted(spec.variables)}
