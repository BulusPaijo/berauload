"""Pure historical-calculation rules using the existing V1.1 formula interpreter."""
from __future__ import annotations
import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from typing import Iterable
from ..formulas.engine import FormulaError, MissingValue, evaluate, validate, parse_formula
from ..units.formula import validate_units, evaluate_units

ALLOWED_MODES = {'period', 'moving_avg', 'yoy'}
ALLOWED_AGG = {'AVG', 'MAX', 'MIN', 'SUM'}
ALLOWED_RES = {'day', 'month', 'year'}


def valid_definition(cfg: dict, source_units: dict[str, str], registry=None):
    if cfg['mode'] not in ALLOWED_MODES or cfg['aggregation'] not in ALLOWED_AGG:
        raise FormulaError('Jenis perhitungan/agregasi tidak dikenal')
    if cfg['resolution'] not in ALLOWED_RES:
        raise FormulaError('Resolusi tidak dikenal')
    if cfg['mode'] == 'moving_avg' and (cfg['resolution'] != 'day' or cfg['aggregation'] != 'AVG'):
        raise FormulaError('Moving average menggunakan rata-rata harian')
    if cfg['mode'] == 'yoy' and cfg['resolution'] != 'month':
        raise FormulaError('YoY menggunakan resolusi bulanan')
    if not 2 <= cfg['moving_days'] <= 30:
        raise FormulaError('Jendela moving average 2–30 hari')
    if not 0 <= cfg['hour_start'] <= cfg['hour_end'] <= 23:
        raise FormulaError('Jam mulai/akhir harus 00–23 dan tidak melintasi tengah malam')
    spec = (validate_units(cfg['expression'], cfg['unit'], source_units, registry)
            if registry else validate(cfg['expression'], cfg['unit'], source_units))
    if cfg['aggregation'] == 'SUM' and cfg['unit'] not in ('1', '—'):
        raise FormulaError('SUM lintas jam hanya untuk indikator tanpa dimensi (mis. IF kondisi = 1)')
    return spec.variables


def validate_range(start: date, end: date, resolution: str):
    if end < start or start.year < 2000 or end.year > 2100:
        raise FormulaError('Periode tidak valid')
    days = (end - start).days + 1
    limit = {'day': 366, 'month': 3660, 'year': 12785}[resolution]
    if days > limit:
        raise FormulaError(f'Rentang maksimal {limit} hari pada resolusi {resolution}')


def period_key(day: date, resolution: str) -> str:
    if resolution == 'day': return day.isoformat()
    if resolution == 'month': return day.strftime('%Y-%m')
    return str(day.year)


def period_days(key: str) -> int:
    if len(key) == 10: return 1
    if len(key) == 7:
        y, m = (int(x) for x in key.split('-'))
        return calendar.monthrange(y, m)[1]
    y = int(key)
    return 366 if calendar.isleap(y) else 365


def iterate_periods(start: date, end: date, resolution: str):
    current = start
    while current <= end:
        yield period_key(current, resolution)
        if resolution == 'day': current += timedelta(days=1)
        elif resolution == 'month':
            current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        else: current = date(current.year + 1, 1, 1)


@dataclass
class Accumulator:
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    count: int = 0

    def add(self, value: float):
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.count += 1

    def result(self, method: str) -> float | None:
        if self.count == 0: return None
        if method == 'AVG': value = self.total / self.count
        elif method == 'MAX': value = self.maximum
        elif method == 'MIN': value = self.minimum
        else: value = self.total
        return round(value, 5) if value is not None and isfinite(value) else None


def accumulate(rows: Iterable[tuple], cfg: dict, resolution: str, source_units=None, registry=None):
    """Evaluate V1.1 expression once per complete hourly observation."""
    buckets: dict[str, Accumulator] = defaultdict(Accumulator)
    last_hour = None
    values: dict[str, float] = {}
    skipped = 0
    use_units = bool(registry and source_units and any(
        source_units.get(ref) != cfg['unit'] for ref in parse_formula(cfg['expression'])[1]))

    def finish():
        nonlocal skipped
        if last_hour is None: return
        day, hour = last_hour
        if not cfg['hour_start'] <= hour <= cfg['hour_end']: return
        try:
            value = (evaluate_units(cfg['expression'], values, cfg['unit'], source_units, registry)
                     if use_units else evaluate(cfg['expression'], values))
            buckets[period_key(day, resolution)].add(value)
        except (MissingValue, FormulaError):
            skipped += 1

    for day, hour, code, value in rows:
        key = (day, hour)
        if key != last_hour:
            finish()
            values = {}
            last_hour = key
        values[code] = float(value)
    finish()
    return buckets, skipped


def _entry(key: str, bucket: Accumulator, cfg: dict):
    expected = period_days(key) * (cfg['hour_end'] - cfg['hour_start'] + 1)
    return {'period': key, 'value': bucket.result(cfg['aggregation']),
            'count': bucket.count, 'expected': expected,
            'coverage_pct': round(100 * bucket.count / expected, 2),
            'complete': bucket.count == expected}


def compute(cfg: dict, rows: Iterable[tuple], start: date, end: date, source_units=None, registry=None):
    """Pure post-query calculation, with explicit missingness and completeness."""
    resolution = 'day' if cfg['mode'] == 'moving_avg' else cfg['resolution']
    buckets, skipped = accumulate(rows, cfg, resolution, source_units, registry)
    rolling_start = start - timedelta(days=cfg['moving_days'] - 1) if cfg['mode'] == 'moving_avg' else start
    result = [_entry(key, buckets.get(key, Accumulator()), cfg)
              for key in iterate_periods(rolling_start, end, resolution)]
    if cfg['mode'] == 'moving_avg':
        result = [item for item in moving_average(result, cfg['moving_days'])
                  if item['period'] >= start.isoformat()]
    if cfg['mode'] == 'yoy':
        result = yoy_results(result, buckets, cfg)
    return {'data': result, 'skipped_incomplete_hours': skipped,
            'note': 'Hasil dihitung dari data tersimpan; belum lengkap bila coverage <100%. Tidak mengubah data sumber.'}


def moving_average(data: list[dict], window: int):
    """Strictly calendar-day windows; no silent bridging of missing days."""
    source = [dict(item) for item in data]
    for idx, item in enumerate(data):
        past = source[max(0, idx - window + 1):idx + 1]
        item['count'] = sum(int(p['count']) for p in past)
        item['expected'] = window * int(source[idx]['expected'])
        item['coverage_pct'] = round(item['count'] * 100 / item['expected'], 2)
        full = len(past) == window and all(p['complete'] for p in past)
        item['value'] = round(sum(float(p['value']) for p in past) / window, 5) if full else None
        item['complete'] = full
        item['rolling_days'] = window
    return data


def yoy_results(data: list[dict], buckets: dict[str, Accumulator], cfg: dict):
    for item in data:
        year, month = (int(x) for x in item['period'].split('-'))
        previous_key = f'{year - 1}-{month:02d}'
        previous = _entry(previous_key, buckets.get(previous_key, Accumulator()), cfg)
        current = item['value']
        old = previous['value']
        item['previous_value'] = old
        item['current_value'] = current
        item['comparable'] = item['complete'] and previous['complete']
        item['value'] = round((current / old - 1) * 100, 5) if old not in (0, None) and current is not None else None
        item['complete'] = item['comparable'] and item['value'] is not None
    return data
