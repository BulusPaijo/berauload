"""Pure, bounded unit conversions. Never converts or rewrites stored readings."""
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite


@dataclass(frozen=True)
class UnitSpec:
    code: str
    dimension: str
    factor: Decimal


class UnitError(ValueError):
    pass


def convert(value: float, source: UnitSpec, target: UnitSpec) -> float:
    if source.dimension != target.dimension:
        raise UnitError(f'Besaran tidak kompatibel: {source.code} dan {target.code}')
    if source.factor <= 0 or target.factor <= 0:
        raise UnitError('Faktor konversi harus lebih besar dari nol')
    if not isfinite(value):
        raise UnitError('Nilai tidak valid')
    return float(Decimal(str(value)) * source.factor / target.factor)


def profile(rows):
    return {r.code: UnitSpec(r.code, r.dimension, Decimal(str(r.factor))) for r in rows}


def check_result_unit(input_unit: str, output_unit: str, mapping: dict[str, UnitSpec]):
    if input_unit not in mapping or output_unit not in mapping:
        raise UnitError('Satuan tidak terdaftar')
    if mapping[input_unit].dimension != mapping[output_unit].dimension:
        raise UnitError('Satuan keluaran tidak kompatibel')
