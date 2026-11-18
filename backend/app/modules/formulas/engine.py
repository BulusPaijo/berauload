"""Deterministic, bounded, Excel-like arithmetic for user-defined metrics.

No eval/exec, attribute access, subscript, imports, or arbitrary Python calls.
The interpreter accepts numeric formulas only; user formulas cannot run code.
"""
from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

FUNCTIONS = frozenset({'SUM', 'AVG', 'MIN', 'MAX', 'ABS', 'ROUND', 'IF', 'AND', 'OR'})
OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
       ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq)


class FormulaError(ValueError):
    pass


class MissingValue(FormulaError):
    def __init__(self, names: set[str]):
        self.names = names
        super().__init__('Data belum lengkap: ' + ', '.join(sorted(names)))


@dataclass(frozen=True)
class FormulaSpec:
    expression: str
    variables: frozenset[str]
    unit: str


@lru_cache(maxsize=512)
def parse_formula(expression: str, extra_functions: frozenset[str] = frozenset()) -> tuple[ast.Expression, frozenset[str]]:
    if not 1 <= len(expression) <= 500:
        raise FormulaError('Panjang rumus harus 1–500 karakter')
    try:
        # Excel-style '=' is accepted ONLY in the opt-in gardu context.
        source = re.sub(r'(?<![<>=!])=(?!=)', '==', expression) if extra_functions else expression
        tree = ast.parse(source, mode='eval')
    except (SyntaxError, ValueError) as exc:
        if extra_functions and isinstance(exc, SyntaxError):
            raise FormulaError(f'Sintaks rumus tidak valid di posisi {exc.offset or 1}') from exc
        raise FormulaError('Sintaks rumus tidak valid') from exc
    if len(list(ast.walk(tree))) > 85:
        raise FormulaError('Rumus terlalu kompleks')
    variables: set[str] = set()

    def inspect(node: ast.AST, depth: int = 0) -> None:
        if depth > 16:
            raise FormulaError('Rumus terlalu dalam')
        if isinstance(node, ast.Expression):
            return inspect(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise FormulaError('Hanya konstanta angka diperbolehkan')
            if not math.isfinite(node.value) or abs(node.value) > 1e12:
                raise FormulaError('Angka konstanta di luar batas')
            return
        if isinstance(node, ast.Name):
            if node.id in FUNCTIONS | extra_functions:
                raise FormulaError('Fungsi harus memakai tanda kurung')
            variables.add(node.id)
            return
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return inspect(node.operand, depth + 1)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            inspect(node.left, depth + 1)
            return inspect(node.right, depth + 1)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], OPS):
            inspect(node.left, depth + 1)
            return inspect(node.comparators[0], depth + 1)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in FUNCTIONS | extra_functions or node.keywords or not 1 <= len(node.args) <= 12:
                raise FormulaError('Fungsi atau jumlah argumen tidak didukung')
            sizes = {'SUM_JURUSAN': (1,), 'MAX_JURUSAN': (1,),
                     'MIN_JURUSAN': (1,), 'AVG_JURUSAN': (1,),
                     'KOSONG': (1,), 'FLAG': (2,), 'IF': (3,), 'ABS': (1,), 'ROUND': (1, 2), 'AND': (2, 3, 4), 'OR': (2, 3, 4)}
            if node.func.id in sizes and len(node.args) not in sizes[node.func.id]:
                raise FormulaError(f'Jumlah argumen {node.func.id} tidak valid')
            for arg in node.args:
                inspect(arg, depth + 1)
            return
        raise FormulaError('Operasi tidak diizinkan dalam rumus')

    inspect(tree)
    if not variables:
        raise FormulaError('Rumus harus memakai minimal satu parameter')
    return tree, frozenset(variables)


def _dimension(node: ast.AST, units: Mapping[str, str]) -> str:
    """Validate units for arithmetic, with constants treated as scalars."""
    if isinstance(node, ast.Expression):
        return _dimension(node.body, units)
    if isinstance(node, ast.Constant):
        return '#number'
    if isinstance(node, ast.Name):
        return '1' if units[node.id] in ('%', '1', '—') else units[node.id]
    if isinstance(node, ast.UnaryOp):
        return _dimension(node.operand, units)
    if isinstance(node, ast.Compare):
        a, b = _dimension(node.left, units), _dimension(node.comparators[0], units)
        if a != b and a != '#number' and b != '#number':
            raise FormulaError(f'Perbandingan beda satuan: {a} dan {b}')
        return 'boolean'
    if isinstance(node, ast.BinOp):
        a, b = _dimension(node.left, units), _dimension(node.right, units)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if a != b and a != '#number' and b != '#number':
                raise FormulaError(f'Penjumlahan/pengurangan beda satuan: {a} dan {b}')
            return b if a == '#number' else a
        if isinstance(node.op, ast.Mult):
            if a in ('1', '#number'): return b
            if b in ('1', '#number'): return a
            return f'{a}*{b}'
        if b in ('1', '#number'): return a
        if a == b: return '1'
        return f'{a}/{b}'
    if isinstance(node, ast.Call):
        fn = node.func.id
        dims = [_dimension(n, units) for n in node.args]
        if fn in ('SUM', 'AVG', 'MIN', 'MAX'):
            specific = {d for d in dims if d != '#number'}
            if len(specific) > 1:
                raise FormulaError('Fungsi agregat mencampur satuan')
            return next(iter(specific), '#number')
        if fn == 'IF':
            if dims[0] not in ('boolean', '#number', '1'):
                raise FormulaError('Kondisi IF harus berupa perbandingan')
            if dims[1] != dims[2] and '#number' not in (dims[1], dims[2]):
                raise FormulaError('Cabang IF harus memiliki satuan sama')
            return dims[2] if dims[1] == '#number' else dims[1]
        if fn in ('AND', 'OR'):
            if any(d not in ('boolean', '1', '#number') for d in dims):
                raise FormulaError('AND/OR membutuhkan kondisi logis')
            return 'boolean'
        return dims[0]
    raise FormulaError('Ekspresi tidak didukung')


def validate(expression: str, unit: str, source_units: Mapping[str, str]) -> FormulaSpec:
    tree, variables = parse_formula(expression)
    unknown = variables - source_units.keys()
    if unknown:
        raise FormulaError('Parameter tidak dikenal: ' + ', '.join(sorted(unknown)))
    dimension = _dimension(tree, source_units)
    expected = '1' if unit in ('%', '1', '—') else unit
    if dimension not in (expected, '#number'):
        raise FormulaError(f'Hasil rumus bersatuan {dimension}, bukan {unit}')
    if dimension == 'boolean':
        raise FormulaError('Gunakan IF untuk mengubah kondisi menjadi angka')
    return FormulaSpec(expression, variables, unit)


def evaluate(expression: str, values: Mapping[str, float]) -> float:
    tree, refs = parse_formula(expression)
    missing = refs - values.keys()
    if missing:
        raise MissingValue(set(missing))

    def walk(node: ast.AST) -> float | bool:
        if isinstance(node, ast.Expression): return walk(node.body)
        if isinstance(node, ast.Constant): return float(node.value)
        if isinstance(node, ast.Name): return float(values[node.id])
        if isinstance(node, ast.UnaryOp):
            x = float(walk(node.operand))
            return -x if isinstance(node.op, ast.USub) else x
        if isinstance(node, ast.BinOp):
            a, b = float(walk(node.left)), float(walk(node.right))
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if b == 0: raise FormulaError('Pembagian dengan nol')
            return a / b
        if isinstance(node, ast.Compare):
            a, b = walk(node.left), walk(node.comparators[0]); op = node.ops[0]
            return (a > b if isinstance(op, ast.Gt) else a >= b if isinstance(op, ast.GtE)
                    else a < b if isinstance(op, ast.Lt) else a <= b if isinstance(op, ast.LtE)
                    else a == b if isinstance(op, ast.Eq) else a != b)
        fn = node.func.id
        if fn == 'IF': return walk(node.args[1] if bool(walk(node.args[0])) else node.args[2])
        if fn == 'AND': return all(bool(walk(a)) for a in node.args)
        if fn == 'OR': return any(bool(walk(a)) for a in node.args)
        args = [float(walk(a)) for a in node.args]
        if fn == 'SUM': return sum(args)
        if fn == 'AVG': return sum(args) / len(args)
        if fn == 'MIN': return min(args)
        if fn == 'MAX': return max(args)
        if fn == 'ABS': return abs(args[0])
        if fn == 'ROUND':
            digits = int(args[1]) if len(args) == 2 else 0
            if digits != (args[1] if len(args) == 2 else 0) or not -5 <= digits <= 5:
                raise FormulaError('ROUND menerima digit bulat -5 s.d. 5')
            return round(args[0], digits)
        raise FormulaError('Fungsi tidak didukung')

    result = walk(tree)
    if isinstance(result, bool): raise FormulaError('Hasil harus berupa angka, bukan boolean')
    if not math.isfinite(result) or not -1e9 < result < 1e9:
        raise FormulaError('Hasil di luar batas numerik sistem')
    return round(result, 5)


# Extensions below are opt-in ONLY for gardu calculations. Legacy validate/evaluate
# retain their exact accepted grammar, missing-data semantics and rounding.
GARDU_FUNCTIONS = frozenset({'SUM_JURUSAN', 'MAX_JURUSAN', 'MIN_JURUSAN',
                             'AVG_JURUSAN', 'KOSONG', 'FLAG'})


def evaluate_gardu(expression, variables, aggregates, flags, *, skip_missing=False,
                   absent_lines=frozenset(), not_applicable=None):
    """Use the existing bounded AST parser; evaluate three-valued gardu cells.

    aggregates: code -> sequence of (existing, numeric or None). Only existing
    jurusan are included. Numeric 0 is never considered missing.
    Returns (value, missing-names, complete-count, source-count).
    """
    tree, _ = parse_formula(expression, GARDU_FUNCTIONS)
    missing = set()
    partial = set()
    touched = set()

    def symbol(node):
        if not isinstance(node, ast.Name):
            raise FormulaError('Argumen fungsi gardu harus kode, bukan ekspresi')
        return node.id

    def walk(node):
        if isinstance(node, ast.Expression): return walk(node.body)
        if isinstance(node, ast.Constant): return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in absent_lines:
                if not_applicable is not None: not_applicable.add(node.id)
                return None
            touched.add(node.id)
            value = variables.get(node.id)
            if value is None: missing.add(node.id)
            return value
        if isinstance(node, ast.UnaryOp):
            x = walk(node.operand)
            return None if x is None else (-x if isinstance(node.op, ast.USub) else +x)
        if isinstance(node, ast.BinOp):
            a, b = walk(node.left), walk(node.right)
            if a is None or b is None: return None
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if b == 0: return None
            return a / b
        if isinstance(node, ast.Compare):
            a, b = walk(node.left), walk(node.comparators[0])
            if a is None or b is None: return None
            op = node.ops[0]
            return (a > b if isinstance(op, ast.Gt) else a >= b if isinstance(op, ast.GtE)
                    else a < b if isinstance(op, ast.Lt) else a <= b if isinstance(op, ast.LtE)
                    else a == b if isinstance(op, ast.Eq) else a != b)
        fn = node.func.id
        if fn == 'IF':
            condition = walk(node.args[0])
            return None if condition is None else walk(node.args[1] if condition else node.args[2])
        if fn in ('AND', 'OR'):
            result = True if fn == 'AND' else False
            unknown = False
            for arg in node.args:
                value = walk(arg)
                if value is None: unknown = True
                elif fn == 'AND' and not bool(value): return False
                elif fn == 'OR' and bool(value): return True
            return None if unknown else result
        if fn in GARDU_FUNCTIONS:
            code = symbol(node.args[0])
            if fn == 'FLAG':
                flag = symbol(node.args[1])
                if code not in flags: raise FormulaError('Parameter flag tidak dikenal: '+code)
                return flag.lower() in flags[code]
            if fn == 'KOSONG':
                if code not in variables and code not in aggregates:
                    raise FormulaError('Parameter tidak dikenal: ' + code)
                if code in aggregates:
                    return all(value is None for value in aggregates[code])
                return variables.get(code) is None
            if code not in aggregates:
                raise FormulaError('Parameter jurusan tidak dikenal: ' + code)
            items = list(aggregates[code])
            touched.update(f'{code}_j{i+1}' for i in range(len(items)))
            valid = [float(x) for x in items if x is not None]
            if len(valid) != len(items):
                missing.update(f'{code}_j{i+1}' for i,x in enumerate(items) if x is None)
                partial.add(code)
            if not valid or (not skip_missing and len(valid) != len(items)):
                return None
            if fn == 'SUM_JURUSAN': return sum(valid)
            if fn == 'MAX_JURUSAN': return max(valid)
            if fn == 'MIN_JURUSAN': return min(valid)
            return sum(valid)/len(valid)
        args = [walk(a) for a in node.args]
        if any(x is None for x in args): return None
        if fn == 'SUM': return sum(args)
        if fn == 'AVG': return sum(args)/len(args)
        if fn == 'MIN': return min(args)
        if fn == 'MAX': return max(args)
        if fn == 'ABS': return abs(args[0])
        if fn == 'ROUND':
            digits = int(args[1]) if len(args) == 2 else 0
            if (len(args) == 2 and digits != args[1]) or not -5 <= digits <= 5:
                raise FormulaError('ROUND menerima digit bulat -5 s.d. 5')
            return round(args[0], digits)
        raise FormulaError('Fungsi tidak dikenal')

    try:
        result = walk(tree)
        if isinstance(result, (float, int)) and not isinstance(result, bool):
            if not math.isfinite(result) or abs(result) >= 1e9: result = None
            elif result is not None: result = round(result, 5)
    except (ZeroDivisionError, OverflowError):
        result = None
    return result, sorted(missing), len(touched - missing), len(touched)
