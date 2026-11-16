"""Pure validation, defaults and formatting of the operator's form layout."""
from fastapi import HTTPException
from .migrations import DEFAULT_TABS

DEFAULT_CODES = {code for code, _ in DEFAULT_TABS}
LEGACY_HIDDEN = {'daya_mampu_sistem_kw'}


def fallback_tab(metric, tab_codes):
    return next((code for code in tab_codes if code == metric.group_name or
                 code.endswith('_' + metric.group_name)),
                next((code for code in tab_codes if code.endswith('_REKAP_LAIN')),
                     next(iter(tab_codes), 'REKAP_LAIN')))


def form_data(tabs, metrics, overrides, version):
    """New metrics appear automatically in their existing group unless overridden."""
    available = {tab.code for tab in tabs}
    return {
        'version': version,
        'tabs': [dict(code=t.code, name=t.name, active=t.active,
                      display_order=t.display_order) for t in tabs],
        'placements': [dict(
            metric_code=m.code,
            tab_code=(overrides[m.code].tab_code if m.code in overrides
                      else fallback_tab(m, available)),
            display_order=(overrides[m.code].display_order if m.code in overrides
                           else m.display_order),
            visible=(overrides[m.code].visible if m.code in overrides
                     else m.code not in LEGACY_HIDDEN),
        ) for m in metrics],
    }


def validate_layout(existing, known_codes, requested_tabs, requested_placements):
    tab_codes = [t.code for t in requested_tabs]
    metric_codes = [p.metric_code for p in requested_placements]
    if len(requested_tabs) > 30 or not any(t.active for t in requested_tabs):
        raise HTTPException(422, 'Harus ada 1–30 tab, minimal satu aktif')
    if len(set(tab_codes)) != len(tab_codes):
        raise HTTPException(422, 'Kode tab tidak boleh duplikat')
    if not {t.code for t in existing}.issubset(set(tab_codes)):
        raise HTTPException(422, 'Tab lama tidak boleh dihapus; gunakan nonaktif')
    if len(set(metric_codes)) != len(metric_codes) or set(metric_codes) != known_codes:
        raise HTTPException(409, 'Daftar parameter berubah; muat ulang sebelum menyimpan')
    if any(p.tab_code not in tab_codes for p in requested_placements):
        raise HTTPException(422, 'Penempatan parameter merujuk ke tab tidak dikenal')
    if not any(p.visible and next(t for t in requested_tabs if t.code == p.tab_code).active
               for p in requested_placements):
        raise HTTPException(422, 'Minimal satu parameter harus tampil pada tab aktif')
