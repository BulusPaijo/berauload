"""Stage 9e: pure what-if logic for overloaded gardu (swap transformer / move load).

No database access and no electrical constants here. The caller supplies an
`evaluate(node, adjust)` callback that runs the normal gardu formula engine, so the
overload threshold stays the admin-managed category rule, never a number in this file.
Nothing here writes data; results are advice, not a technical decision.
"""
from math import asin, cos, radians, sin, sqrt

CURRENT_CODES = ('i_r', 'i_s', 'i_t', 'i_n')
REQUIRED_CODES = ('i_r', 'i_s', 'i_t')   # a line is movable only with all three phases filled
OVERLOAD_CODE = 'overload'


def distance_km(lat1, lon1, lat2, lon2):
    """Straight-line (haversine) distance; NOT the length of the network."""
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(a))


def is_ok(ev):
    """Assessable and not overloaded. A NULL result is never treated as fine."""
    return ev is not None and ev.get('overload') is False


def movable_lines(node):
    out = []
    for no, values in sorted(node['lines'].items()):
        if all(values.get(c) is not None for c in REQUIRED_CODES) and \
                any(values[c] > 0 for c in REQUIRED_CODES):
            out.append(no)
    return out


def target_line(node):
    for no, values in sorted(node['lines'].items()):
        if all(values.get(c) is not None for c in REQUIRED_CODES):
            return no
    return None


def trafo_adjust(kva, phase):
    def adjust(variables, aggregates):
        variables['kva'] = float(kva)
        variables['fase'] = float(phase)
    return adjust


def scale_line(line, factor):
    def adjust(variables, aggregates):
        for code in CURRENT_CODES:
            key = f'{code}_j{line}'
            if variables.get(key) is None:
                continue
            variables[key] = variables[key] * factor
            if code in aggregates:
                aggregates[code][line - 1] = variables[key]
    return adjust


def add_to_line(line, amounts):
    def adjust(variables, aggregates):
        for code, amount in amounts.items():
            key = f'{code}_j{line}'
            if amount is None or variables.get(key) is None:
                continue          # never create a number where the reading is empty
            variables[key] = variables[key] + amount
            if code in aggregates:
                aggregates[code][line - 1] = variables[key]
    return adjust


def moved_amounts(source, line, portion):
    return {c: (None if source['lines'][line].get(c) is None
                else source['lines'][line][c] * portion / 100.0) for c in CURRENT_CODES}


def lines_after(node, adjust=None):
    """Per-line currents after an adjustment, built only from the node's own readings."""
    variables = {'kva': node['kva'], 'fase': node['phase']}
    aggregates = {c: [] for c in CURRENT_CODES}
    for no in range(1, node['line_count'] + 1):
        values = node['lines'].get(no, {})
        for c in CURRENT_CODES:
            variables[f'{c}_j{no}'] = values.get(c)
            aggregates[c].append(values.get(c))
    if adjust:
        adjust(variables, aggregates)
    return [{'line_no': no, **{c: variables.get(f'{c}_j{no}') for c in CURRENT_CODES}}
            for no in range(1, node['line_count'] + 1)], variables


def swap_option(evaluate, x, z):
    ex = evaluate(x, trafo_adjust(z['kva'], z['phase']))
    ez = evaluate(z, trafo_adjust(x['kva'], x['phase']))
    reason = None
    if ex is None or ez is None or ex.get('overload') is None or ez.get('overload') is None:
        reason = 'Beban sesudah tukar tidak dapat dinilai'
    elif not is_ok(ex):
        reason = 'Gardu ini tetap overload setelah tukar trafo'
    elif not is_ok(ez):
        reason = 'Gardu tujuan menjadi overload setelah tukar trafo'
    return {'feasible': reason is None, 'reason': reason,
            'x_after': ex and ex.get('persen'), 'z_after': ez and ez.get('persen')}


def move_option(evaluate, x, z, line):
    """Feasible portion range [p_min, p_max] in whole percent, found by bisection.

    Assumes more moved current means less load at the source and more at the target,
    which holds for the linear load formulas; endpoints are checked explicitly.
    """
    tline = target_line(z)
    if tline is None:
        return {'feasible': False, 'reason': 'Arus gardu tujuan tidak lengkap'}

    def x_ok(p):
        return is_ok(evaluate(x, scale_line(line, 1 - p / 100.0)))

    def z_ok(p):
        return is_ok(evaluate(z, add_to_line(tline, moved_amounts(x, line, p))))

    if not x_ok(100):
        return {'feasible': False, 'reason': 'Memindahkan seluruh jurusan ini belum cukup'}
    lo, hi = 1, 100
    while lo < hi:
        mid = (lo + hi) // 2
        if x_ok(mid):
            hi = mid
        else:
            lo = mid + 1
    p_min = lo
    if not z_ok(1):
        return {'feasible': False, 'reason': 'Gardu tujuan menjadi overload walau hanya sedikit beban dipindah'}
    lo, hi = 1, 100
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if z_ok(mid):
            lo = mid
        else:
            hi = mid - 1
    p_max = lo
    if p_min > p_max:
        return {'feasible': False, 'reason': 'Tidak ada porsi yang membuat kedua gardu aman',
                'p_min': p_min, 'p_max': p_max, 'target_line': tline}
    return {'feasible': True, 'reason': None, 'p_min': p_min, 'p_max': p_max, 'target_line': tline}


def review_swap(evaluate, x, z):
    ax, az = trafo_adjust(z['kva'], z['phase']), trafo_adjust(x['kva'], x['phase'])
    return [_side(evaluate, x, ax, z['kva'], z['phase']),
            _side(evaluate, z, az, x['kva'], x['phase'])]


def review_move(evaluate, x, z, line, portion):
    tline = target_line(z)
    ax = scale_line(line, 1 - portion / 100.0)
    az = add_to_line(tline, moved_amounts(x, line, portion))
    return [_side(evaluate, x, ax, x['kva'], x['phase']),
            _side(evaluate, z, az, z['kva'], z['phase'])]


def _side(evaluate, node, adjust, kva_after, phase_after):
    before, after = evaluate(node, None), evaluate(node, adjust)
    lines_b, _ = lines_after(node)
    lines_a, _ = lines_after(node, adjust)
    return {'id': node['id'], 'code': node['code'], 'name': node['name'],
            'kva_before': node['kva'], 'kva_after': kva_after,
            'phase_before': node['phase'], 'phase_after': phase_after,
            'before': before, 'after': after, 'lines_before': lines_b, 'lines_after': lines_a}
