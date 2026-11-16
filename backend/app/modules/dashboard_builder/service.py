"""Pure layout invariants and schema validation, separate from database and UI."""
from fastapi import HTTPException
from .visualization import NEW_KINDS, validate_visual
from .panel_style import validate_panel_style

KINDS = {'line', 'area', 'bar', 'stat', 'gauge', 'table', 'rule'} | NEW_KINDS
SOURCES = {'metric', 'historical', 'engineering'}
AGGREGATIONS = {'avg', 'peak', 'min'}
MAX_PANELS = 16
MAX_DASHBOARDS = 40
WIDTHS = set(range(3, 13))
LEGACY_HIDDEN = {'daya_mampu_sistem_kw'}


def validate_panels(panels: list[dict], unit_for: dict[str, str],
                    historical_ids: set[int], rule_ids: set[int], unit_specs=None, pair=None) -> list[dict]:
    if len(panels) > MAX_PANELS:
        raise HTTPException(422, f'Maksimal {MAX_PANELS} panel per dashboard')
    ids = set()
    cleaned = []
    for panel in panels:
        pid = panel['id']
        if pid in ids:
            raise HTTPException(422, 'ID panel tidak boleh berulang')
        ids.add(pid)
        kind, source = panel['kind'], panel['source']
        if kind not in KINDS or source not in SOURCES:
            raise HTTPException(422, 'Jenis panel / sumber tidak didukung')
        if panel['w'] not in WIDTHS or not 1 <= panel['h'] <= 4:
            raise HTTPException(422, 'Ukuran panel tidak valid')
        if panel['aggregation'] not in AGGREGATIONS:
            raise HTTPException(422, 'Metode agregasi tidak valid')
        codes = panel['metric_codes']
        source_id = panel['source_id']
        if source == 'metric':
            if kind == 'rule' or not 1 <= len(codes) <= (1 if kind in {'stat', 'gauge'} else 4):
                raise HTTPException(422, 'Jumlah parameter panel tidak valid')
            if len(set(codes)) != len(codes) or any(c not in unit_for or c in LEGACY_HIDDEN for c in codes):
                raise HTTPException(422, 'Parameter tidak tersedia / duplikat')
            if len({unit_for[c] for c in codes}) != 1:
                dims = {unit_specs[unit_for[c]].dimension for c in codes
                        if unit_specs and unit_for[c] in unit_specs}
                if not (panel.get('display_unit') and len(dims) == 1 and
                        all(unit_for[c] in unit_specs for c in codes)):
                    raise HTTPException(422, 'Satuan berbeda membutuhkan konversi tampilan yang kompatibel')
            if pair and set(pair).issubset(codes):
                if len(codes) != 2 or panel['aggregation'] != 'avg':
                    raise HTTPException(422, 'Perbandingan H/J hanya untuk dua seri berpasangan, metode rata-rata')
        elif source == 'historical':
            if kind not in {'line', 'area', 'bar', 'step', 'stat', 'table'} or source_id not in historical_ids:
                raise HTTPException(422, 'Formula historis tidak ditemukan atau jenis panel tidak sesuai')
            if codes:
                raise HTTPException(422, 'Panel historis tidak boleh memuat parameter langsung')
        else:
            if kind != 'rule' or source_id not in rule_ids or codes:
                raise HTTPException(422, 'Aturan engineering harus aktif dan memakai panel Status')
        validate_visual(panel, unit_for, unit_specs, pair)
        validate_panel_style(panel)
        cleaned.append(dict(panel))
    return cleaned


def may_edit(layout, user) -> bool:
    return user.role == 'admin' if layout.scope == 'system' else layout.owner_id == user.id


def may_view(layout, user) -> bool:
    return layout.scope == 'system' or layout.owner_id == user.id
