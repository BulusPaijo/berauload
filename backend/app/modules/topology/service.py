"""Pure, strict JSON layout validation; no database access or electrical assumptions."""
from __future__ import annotations
import re
from copy import deepcopy

SYMBOL_TYPES = frozenset({'generator', 'incoming', 'busbar', 'breaker',
                          'transformer', 'feeder', 'load', 'capacitor'})
BOX_TYPES = frozenset({'metric', 'summary', 'ranking', 'legend', 'text'})
AREA_BORDERS = frozenset({'solid', 'dashed', 'dotted'})
AREA_COLORS = frozenset({'teal', 'blue', 'amber', 'green', 'red', 'gray'})
MAX_CANVAS = 20000  # SVG configuration only, not a measurement limit
# Only an explicit sample 20 kV rendering level and a neutral, unspecified level.
# Adding other levels requires approval; these are NOT equipment ratings.
WIRE_LEVELS = frozenset({'20kv', 'unspecified'})
ID_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,59}$')
CODE_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,89}$')
FORBIDDEN = re.compile(r'[<>{}`;]|--|/\*|\*/|javascript:|on(?:error|load|click)\s*=|\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EVAL)\s', re.I)


class TopologyError(ValueError):
    pass


def fail(message: str):
    raise TopologyError(message)


def keys(value, required, optional=()):
    if not isinstance(value, dict):
        fail('Objek JSON harus berupa object')
    if not set(required).issubset(value) or set(value) - set(required) - set(optional):
        fail('Field layout tidak lengkap atau berisi field tidak diizinkan')


def number(value, label, low, high, grid=1):
    if type(value) is not int or not low <= value <= high or value % grid:
        fail(f'{label}: angka/batas/grid tidak valid')


def string(value, label, maximum=120, allow_empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        fail(f'{label}: teks tidak valid')
    if any(ord(c) < 32 for c in value) or FORBIDDEN.search(value):
        fail(f'{label}: hanya teks biasa yang diizinkan')


def code(value, label):
    if not isinstance(value, str) or not CODE_PATTERN.fullmatch(value):
        fail(f'{label}: kode tidak valid')


def object_id(value, used):
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value) or value in used:
        fail('ID objek wajib unik dan alfanumerik')
    used.add(value)


def asset(value, assets):
    if value is not None and (not isinstance(value, str) or value not in assets):
        fail('Peralatan tidak tersedia atau tidak aktif')


def position(obj, canvas, grid, is_box=False):
    for field in ('x', 'y', 'w'):
        number(obj[field], field, 0 if field != 'w' else grid,
               canvas['w'] if field != 'y' else canvas['h'], grid)
    height = grid if is_box else obj['h']
    if not is_box:
        number(height, 'h', grid, canvas['h'], grid)
    if obj['x'] + obj['w'] > canvas['w'] or obj['y'] + height > canvas['h']:
        fail('Objek berada di luar kanvas')


def validate_symbol(symbol, canvas, grid, used, assets):
    keys(symbol, ('id', 'type', 'x', 'y', 'w', 'h', 'asset_code', 'label', 'rotation'), ('link',))
    object_id(symbol['id'], used)
    if not isinstance(symbol['type'], str) or symbol['type'] not in SYMBOL_TYPES:
        fail('Jenis simbol tidak dikenal')
    position(symbol, canvas, grid)
    asset(symbol['asset_code'], assets)
    string(symbol['label'], 'Label simbol', 120)
    if type(symbol['rotation']) is not int or symbol['rotation'] not in (0, 90, 180, 270):
        fail('Rotasi hanya 0, 90, 180, atau 270')

    if 'link' in symbol:
        link = symbol['link']
        keys(link, ('unit_id', 'diagram_id'))
        number(link['unit_id'], 'link.unit_id', 1, 2147483647)
        number(link['diagram_id'], 'link.diagram_id', 1, 2147483647)


def validate_wire(wire, canvas, grid, used):
    keys(wire, ('id', 'points', 'level'))
    object_id(wire['id'], used)
    if not isinstance(wire['level'], str) or wire['level'] not in WIRE_LEVELS:
        fail('Level tegangan belum diizinkan')
    points = wire['points']
    if not isinstance(points, list) or not 2 <= len(points) <= 32:
        fail('Garis memerlukan 2–32 titik')
    if any(points[i] == points[i-1] for i in range(1, len(points))):
        fail('Dua titik garis berurutan tidak boleh sama')
    for p in points:
        if not isinstance(p, list) or len(p) != 2:
            fail('Titik garis harus pasangan [x,y]')
        number(p[0], 'wire.x', 0, canvas['w'], grid)
        number(p[1], 'wire.y', 0, canvas['h'], grid)


def validate_box(box, canvas, grid, used, assets, metrics, rules):
    required = ('id', 'kind', 'x', 'y', 'w', 'title', 'asset_code', 'metric_codes',
                'decimals', 'show_unit', 'leader', 'sparkline', 'locked', 'rule_id',
                'anchor_symbol_id')
    keys(box, required)
    object_id(box['id'], used)
    if not isinstance(box['kind'], str) or box['kind'] not in BOX_TYPES:
        fail('Jenis kotak tidak dikenal')
    position(box, canvas, grid, is_box=True)
    string(box['title'], 'Judul kotak', 120)
    asset(box['asset_code'], assets)
    codes = box['metric_codes']
    if not isinstance(codes, list) or len(codes) > 6 or len(codes) != len(set(map(str, codes))):
        fail('Maksimal 6 parameter unik per kotak')
    if box['kind'] in ('metric', 'summary', 'ranking') and not codes:
        fail('Kotak pengukuran, ringkasan dan peringkat memerlukan 1–6 parameter')
    if box['kind'] in ('legend', 'text') and codes:
        fail('Kotak legenda atau teks tidak boleh menyimpan parameter')
    for item in codes:
        code(item, 'Kode parameter')
        if item == 'daya_mampu_sistem_kw' or item not in metrics:
            fail('Parameter tidak tersedia, legacy, atau tidak aktif')
        if box['asset_code'] is not None and metrics[item][1] != assets[box['asset_code']]:
            fail('Parameter tidak dimiliki peralatan yang dipilih')
    if box['kind'] == 'ranking' and len({metrics[item][0] for item in codes}) > 1:
        fail('Peringkat hanya boleh membandingkan parameter dengan satuan identik')
    number(box['decimals'], 'desimal', 0, 4)
    for field in ('show_unit', 'leader', 'sparkline', 'locked'):
        if type(box[field]) is not bool:
            fail(f'{field}: harus boolean')
    if box['rule_id'] is not None and (type(box['rule_id']) is not int or box['rule_id'] not in rules):
        fail('Engineering Rule tidak aktif atau tidak dikenal')
    if box['anchor_symbol_id'] is not None and not isinstance(box['anchor_symbol_id'], str):
        fail('Anchor simbol tidak valid')


def validate_area(area, canvas, grid, used):
    """Visual grouping only; it is never an electrical node or measurement."""
    keys(area, ('id', 'x', 'y', 'w', 'h', 'title', 'border', 'color',
                'opacity', 'locked'))
    object_id(area['id'], used)
    position(area, canvas, grid)
    string(area['title'], 'Judul area', 100)
    if not isinstance(area['border'], str) or area['border'] not in AREA_BORDERS:
        fail('Jenis garis area tidak diizinkan')
    if not isinstance(area['color'], str) or area['color'] not in AREA_COLORS:
        fail('Warna area tidak diizinkan')
    number(area['opacity'], 'Opasitas area', 0, 40, 5)
    if type(area['locked']) is not bool:
        fail('Kunci area harus boolean')


def validate_layout(layout, assets: dict, metrics: dict, rules: set[int]):
    """Accept only the documented structure; returns a defensive JSON copy."""
    keys(layout, ('canvas', 'symbols', 'wires', 'boxes'), ('areas',))
    canvas = layout['canvas']
    keys(canvas, ('w', 'h', 'grid'))
    number(canvas['grid'], 'grid', 10, 10)
    for dimension in ('w', 'h'):
        number(canvas[dimension], dimension, 200, MAX_CANVAS, canvas['grid'])
    for field, limit in (('symbols', 200), ('wires', 300), ('boxes', 100)):
        if not isinstance(layout[field], list) or len(layout[field]) > limit:
            fail(f'Jumlah {field} melebihi batas')
    areas = layout.get('areas', [])
    if not isinstance(areas, list) or len(areas) > 100:
        fail('Maksimal 100 area visual')
    used = set()
    for item in areas:
        validate_area(item, canvas, canvas['grid'], used)
    for item in layout['symbols']:
        validate_symbol(item, canvas, canvas['grid'], used, assets)
    if sum('link' in symbol for symbol in layout['symbols']) > 200:
        fail('Maksimal 200 tautan per diagram')
    symbol_ids = {item['id'] for item in layout['symbols']}
    for item in layout['wires']:
        validate_wire(item, canvas, canvas['grid'], used)
    for item in layout['boxes']:
        validate_box(item, canvas, canvas['grid'], used, assets, metrics, rules)
        if item['anchor_symbol_id'] is not None and item['anchor_symbol_id'] not in symbol_ids:
            fail('Simbol anchor tidak ditemukan')
        if item['leader'] and item['anchor_symbol_id'] is None:
            fail('Garis penghubung memerlukan anchor simbol')
    return deepcopy(layout)


EMPTY_LAYOUT = {'canvas': {'w': 1600, 'h': 900, 'grid': 10},
                'symbols': [], 'wires': [], 'boxes': []}
