"""Dimension-aware extension to the existing V1.1 safe AST engine.

Only numeric expressions are accepted; no eval, dynamic Python, or arbitrary SQL.
Constants in addition/comparisons use the adjacent parameter's unit, e.g.
IF(voltage_kv > 20, ...) interprets 20 in kV.
Percent formula convention stays legacy: ratio*100 produces display percent.
"""
import ast
import math
from dataclasses import dataclass
from .service import UnitSpec, convert, UnitError
from ..formulas.engine import FormulaError, FormulaSpec, MissingValue, parse_formula


@dataclass(frozen=True)
class Quantity:
    value: float | bool
    dimension: str  # numeric, boolean or physical dimension
    unit: str = ''


def validate_units(expression: str, output: str, source_units: dict[str, str],
                   specs: dict[str, UnitSpec]) -> FormulaSpec:
    tree, names = parse_formula(expression)
    unknown = names - source_units.keys()
    if unknown:
        raise FormulaError('Parameter tidak dikenal: ' + ', '.join(sorted(unknown)))
    if output not in specs or any(source_units[n] not in specs for n in names):
        raise FormulaError('Satuan parameter belum ada di Master Satuan')

    def same(a, b):
        if a == b: return a
        if a == 'numeric': return b
        if b == 'numeric': return a
        raise FormulaError(f'Dimensi rumus berbeda: {a} dan {b}')

    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant): return 'numeric'
        if isinstance(n, ast.Name): return specs[source_units[n.id]].dimension
        if isinstance(n, ast.UnaryOp): return visit(n.operand)
        if isinstance(n, ast.Compare):
            same(visit(n.left), visit(n.comparators[0]))
            return 'boolean'
        if isinstance(n, ast.BinOp):
            a, b = visit(n.left), visit(n.right)
            if isinstance(n.op, (ast.Add, ast.Sub)): return same(a, b)
            if isinstance(n.op, ast.Mult):
                if a not in ('numeric', 'ratio') and b not in ('numeric', 'ratio'):
                    raise FormulaError('Perkalian dua besaran berdimensi belum didukung')
                return b if a in ('numeric', 'ratio') else a
            if b in ('numeric', 'ratio'): return a
            if a == b: return 'ratio'
            raise FormulaError('Pembagian beda dimensi belum didukung')
        if isinstance(n, ast.Call):
            fn = n.func.id
            ds = [visit(a) for a in n.args]
            if fn in ('AND', 'OR'):
                if any(x not in ('boolean', 'numeric', 'ratio') for x in ds):
                    raise FormulaError('AND/OR hanya menerima kondisi')
                return 'boolean'
            if fn == 'IF':
                if ds[0] not in ('boolean', 'numeric', 'ratio'):
                    raise FormulaError('IF membutuhkan kondisi logis')
                return same(ds[1], ds[2])
            if fn == 'ROUND':
                if len(ds) == 2 and ds[1] != 'numeric':
                    raise FormulaError('Digit ROUND harus angka')
                return ds[0]
            if fn == 'ABS': return ds[0]
            result = ds[0]
            for d in ds[1:]: result = same(result, d)
            return result
        raise FormulaError('Ekspresi tidak didukung')

    result = visit(tree)
    if result == 'boolean':
        raise FormulaError('Hasil kondisi wajib dibungkus IF menjadi angka')
    expected = specs[output].dimension
    if result not in (expected, 'numeric'):
        raise FormulaError(f'Hasil formula berdimensi {result}, bukan {expected}')
    return FormulaSpec(expression, names, output)


def evaluate_units(expression: str, values: dict[str, float], output: str,
                   source_units: dict[str, str], specs: dict[str, UnitSpec]) -> float:
    tree, names = parse_formula(expression)
    missing = names - values.keys()
    if missing: raise MissingValue(set(missing))

    def compatible(a: Quantity, b: Quantity):
        if a.dimension == b.dimension and a.unit and b.unit and a.unit != b.unit:
            return a, Quantity(convert(float(b.value), specs[b.unit], specs[a.unit]), b.dimension, a.unit)
        if a.dimension == 'numeric' and b.dimension != 'numeric':
            return Quantity(a.value, b.dimension, b.unit), b
        if b.dimension == 'numeric' and a.dimension != 'numeric':
            return a, Quantity(b.value, a.dimension, a.unit)
        if a.dimension != b.dimension:
            raise FormulaError('Dimensi operand tidak kompatibel')
        return a, b

    def calc(n) -> Quantity:
        if isinstance(n, ast.Expression): return calc(n.body)
        if isinstance(n, ast.Constant): return Quantity(float(n.value), 'numeric')
        if isinstance(n, ast.Name):
            spec = specs[source_units[n.id]]
            return Quantity(float(values[n.id]), spec.dimension, spec.code)
        if isinstance(n, ast.UnaryOp):
            q = calc(n.operand)
            return Quantity(-float(q.value) if isinstance(n.op, ast.USub) else float(q.value), q.dimension, q.unit)
        if isinstance(n, ast.Compare):
            a, b = compatible(calc(n.left), calc(n.comparators[0]))
            op = n.ops[0]; av, bv = float(a.value), float(b.value)
            result = (av > bv if isinstance(op, ast.Gt) else av >= bv if isinstance(op, ast.GtE)
                      else av < bv if isinstance(op, ast.Lt) else av <= bv if isinstance(op, ast.LtE)
                      else av == bv if isinstance(op, ast.Eq) else av != bv)
            return Quantity(result, 'boolean')
        if isinstance(n, ast.BinOp):
            a, b = calc(n.left), calc(n.right)
            if isinstance(n.op, (ast.Add, ast.Sub)):
                a, b = compatible(a, b)
                return Quantity(float(a.value) + (1 if isinstance(n.op, ast.Add) else -1) * float(b.value), a.dimension, a.unit)
            if isinstance(n.op, ast.Mult):
                if a.dimension not in ('numeric', 'ratio') and b.dimension not in ('numeric', 'ratio'):
                    raise FormulaError('Perkalian dua besaran berdimensi belum didukung')
                return Quantity(float(a.value) * float(b.value), b.dimension if a.dimension in ('numeric', 'ratio') else a.dimension,
                                b.unit if a.dimension in ('numeric', 'ratio') else a.unit)
            if float(b.value) == 0: raise FormulaError('Pembagian dengan nol')
            if a.dimension == b.dimension and a.dimension not in ('numeric', 'ratio'):
                a, b = compatible(a, b)
                return Quantity(float(a.value) / float(b.value), 'ratio')
            if b.dimension in ('numeric', 'ratio'):
                return Quantity(float(a.value) / float(b.value), a.dimension, a.unit)
            raise FormulaError('Pembagian beda dimensi belum didukung')
        fn = n.func.id
        if fn == 'IF': return calc(n.args[1] if bool(calc(n.args[0]).value) else n.args[2])
        if fn == 'AND': return Quantity(all(bool(calc(x).value) for x in n.args), 'boolean')
        if fn == 'OR': return Quantity(any(bool(calc(x).value) for x in n.args), 'boolean')
        args = [calc(x) for x in n.args]
        if fn == 'ABS': return Quantity(abs(float(args[0].value)), args[0].dimension, args[0].unit)
        if fn == 'ROUND':
            digits = float(args[1].value) if len(args) == 2 else 0
            if digits != int(digits) or not -5 <= digits <= 5:
                raise FormulaError('ROUND menerima digit bulat -5 s.d. 5')
            return Quantity(round(float(args[0].value), int(digits)), args[0].dimension, args[0].unit)
        head = next((q for q in args if q.dimension != 'numeric'), args[0])
        normalized = [compatible(head, q)[1] for q in args]
        vals = [float(x.value) for x in normalized]
        number = (sum(vals) if fn == 'SUM' else sum(vals)/len(vals) if fn == 'AVG'
                  else min(vals) if fn == 'MIN' else max(vals))
        return Quantity(number, head.dimension, head.unit)

    result = calc(tree)
    if isinstance(result.value, bool) or result.dimension == 'boolean':
        raise FormulaError('Hasil harus berupa angka')
    if result.unit and result.unit != output:
        try: result = Quantity(convert(float(result.value), specs[result.unit], specs[output]), result.dimension, output)
        except UnitError as exc: raise FormulaError(str(exc)) from exc
    if not math.isfinite(float(result.value)) or not -1e9 < float(result.value) < 1e9:
        raise FormulaError('Hasil di luar batas numerik sistem')
    return round(float(result.value), 5)
