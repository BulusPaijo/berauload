"""Validate selectors, not electrical formulas or historical calculations."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...db import Metric

from ..org_units.roles import main_pair


def default_codes(db, unit_id):
    cap, load = main_pair(db, unit_id)
    return [m.code for m in (cap, load) if m is not None]
LEGACY_HIDDEN = {'daya_mampu_sistem_kw'}
MAX_SERIES = 4


def validate_codes(db: Session, codes: list[str], unit_id=None) -> list[str]:
    if not 1 <= len(codes) <= MAX_SERIES:
        raise HTTPException(422, f'Pilih 1 sampai {MAX_SERIES} parameter grafik')
    if len(set(codes)) != len(codes):
        raise HTTPException(422, 'Parameter grafik tidak boleh duplikat')
    if any(not isinstance(code, str) or len(code) > 90 for code in codes):
        raise HTTPException(422, 'Kode parameter grafik tidak valid')
    if LEGACY_HIDDEN.intersection(codes):
        raise HTTPException(422, 'Parameter daya mampu legacy tidak dipakai untuk grafik')
    rows = db.query(Metric).filter(Metric.code.in_(codes), Metric.active.is_(True), Metric.unit_id==unit_id).all()
    units = {r.unit for r in rows}
    if len(rows) != len(codes):
        raise HTTPException(422, 'Parameter tidak ditemukan atau tidak aktif')
    if len(units) != 1:
        raise HTTPException(422, 'Grafik hanya dapat menggabungkan parameter dengan satuan yang sama')
    return codes
