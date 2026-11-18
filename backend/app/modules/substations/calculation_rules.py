"""Gardu code namespace, bounded AST verification and dependency ordering."""
import ast
import re
from fastapi import HTTPException
from ..formulas.engine import FormulaError, FUNCTIONS, GARDU_FUNCTIONS, parse_formula
from .models import SubstationParam, SubstationValueFlag
from .models_calc import GarduCalcColumn, GarduCalcConstant, GarduCalcRule

IDENT = re.compile(r'^[a-z][a-z0-9_]{0,79}$')
AGG = {'SUM_JURUSAN', 'MIN_JURUSAN', 'MAX_JURUSAN', 'AVG_JURUSAN'}
BUILTIN = {'kva', 'fase', 'jumlah_jurusan'}
SHAPES = {'circle', 'square', 'diamond', 'triangle', 'exclamation'}
COLORS = re.compile(r'^#[0-9a-fA-F]{6}$')


def namespace(db, columns=None, constants=None):
    params = {p.code.lower(): p.scope for p in db.query(SubstationParam).all()}
    cols = {r.code: r for r in (columns if columns is not None
            else db.query(GarduCalcColumn).filter_by(active=True).all())}
    const = {r.code: r for r in (constants if constants is not None
             else db.query(GarduCalcConstant).all())}
    flags = {f.code.lower() for f in db.query(SubstationValueFlag).all()}
    return params, cols, const, flags


def validate_code(code, db, existing=None):
    if not isinstance(code, str) or not IDENT.fullmatch(code):
        raise HTTPException(422, 'Kode harus huruf kecil, diawali huruf, hanya a-z/0-9/_')
    params, cols, const, _ = namespace(db)
    occupied = set(params) | set(cols) | set(const) | BUILTIN
    occupied |= {r.code for r in db.query(GarduCalcColumn).all()} | {p + '_j' + str(i)
                for p in params for i in range(1, 6)} | {n.lower() for n in GARDU_FUNCTIONS}
    occupied |= {'sum', 'min', 'max', 'avg', 'if', 'and', 'or', 'round', 'abs'}
    if code in occupied and code != existing:
        raise HTTPException(409, f'Kode {code} sudah dipakai parameter/konstanta/kolom/fungsi')


def inspect_expression(expression, db, columns=None, constants=None, rule=False):
    try:
        tree, _ = parse_formula(expression, GARDU_FUNCTIONS)
    except FormulaError as exc:
        raise HTTPException(422, str(exc)) from exc
    params, cols, const, flag_codes = namespace(db, columns, constants)
    used, deps = set(), set()
    recognized = BUILTIN | set(const) | set(cols) | {p for p, scope in params.items()
                  if scope == 'substation'}
    recognized |= {f'{p}_j{i}' for p, scope in params.items() if scope == 'line'
                   for i in range(1, 6)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.func.id in GARDU_FUNCTIONS:
            if not isinstance(node.args[0], ast.Name):
                raise HTTPException(422, 'Argumen agregat/FLAG/KOSONG harus kode parameter')
            code = node.args[0].id
            if node.func.id in AGG and params.get(code) != 'line':
                raise HTTPException(422, f'{code} bukan parameter jurusan untuk {node.func.id}')
            if node.func.id == 'FLAG':
                if code not in params and code not in recognized:
                    raise HTTPException(422, f'Parameter flag tidak dikenal: {code}')
                if not isinstance(node.args[1], ast.Name) or node.args[1].id.lower() not in flag_codes:
                    raise HTTPException(422, 'Kode flag tidak dikenal (mis. PUTUS)')
            if node.func.id == 'KOSONG' and code not in recognized and code not in params:
                raise HTTPException(422, f'Parameter KOSONG tidak dikenal: {code}')
            used.add(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or node.id in FUNCTIONS | GARDU_FUNCTIONS:
            continue
        if isinstance(node.ctx, ast.Load):
            raw = node.id
            # Allow only as explicitly designated symbolic function arguments.
            symbolic = any(isinstance(call, ast.Call) and call.func.id in GARDU_FUNCTIONS
                and node in call.args for call in ast.walk(tree) if isinstance(call, ast.Call))
            if symbolic: continue
            if raw not in recognized:
                raise HTTPException(422, f'Nama tidak dikenal pada rumus: {raw}')
            used.add(raw)
            if raw in cols: deps.add(raw)
    if rule and not isinstance(tree.body, (ast.Compare, ast.Call)):
        raise HTTPException(422, 'Syarat harus perbandingan atau fungsi kondisi')
    if rule and isinstance(tree.body, ast.Call) and tree.body.func.id not in {'AND','OR','FLAG','KOSONG','IF'}:
        raise HTTPException(422, 'Syarat harus menghasilkan benar/salah')
    return {'names': sorted(used), 'dependencies': sorted(deps)}


def order_columns(db, draft=None):
    items = db.query(GarduCalcColumn).filter_by(active=True).all()
    if draft and draft.get('kind') == 'column':
        items = [r for r in items if r.code != draft['code']]
        if draft.get('active', True):
            from types import SimpleNamespace
            items.append(SimpleNamespace(**draft))
    codes = {row.code: row for row in items}
    edges = {code: set(inspect_expression(row.expression, db, columns=list(codes.values()))['dependencies'])
             for code, row in codes.items()}
    visit, path, result = set(), [], []

    def traverse(code):
        if code in path:
            chain = path[path.index(code):] + [code]
            raise HTTPException(422, 'Siklus rumus: ' + ' → '.join(chain))
        if code in visit: return
        path.append(code)
        for child in sorted(edges[code]): traverse(child)
        path.pop()
        visit.add(code)
        result.append(codes[code])
    for code in codes: traverse(code)
    return result


def validate_rule_shape(kind, color, marker):
    if kind not in ('category', 'finding'):
        raise HTTPException(422, 'Jenis aturan harus category atau finding')
    if not COLORS.fullmatch(color or '') or marker not in SHAPES:
        raise HTTPException(422, 'Warna harus #RRGGBB dan tanda dari daftar tetap')
