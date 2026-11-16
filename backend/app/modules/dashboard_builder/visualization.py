"""Advanced panel settings validation independent of route/controllers."""
import re
from fastapi import HTTPException

LEGEND = {'bottom', 'top', 'right', 'hidden'}
NEW_KINDS = {'step', 'stacked_bar'}
HEX = re.compile(r'^#[A-Fa-f0-9]{6}$')


def validate_visual(panel: dict, metric_units: dict[str, str], unit_specs, pair=None) -> None:
    colors = panel.get('colors') or {}
    if len(colors) > 4 or any(not HEX.fullmatch(color) for color in colors.values()):
        raise HTTPException(422, 'Warna seri harus format #RRGGBB, maksimal 4')
    allowed_keys = (set(panel['metric_codes']) if panel['source'] == 'metric' else
                    {'value'} if panel['source'] == 'historical' else set())
    if not set(colors).issubset(allowed_keys):
        raise HTTPException(422, 'Warna merujuk seri yang tidak tersedia')
    if panel.get('legend', 'bottom') not in LEGEND:
        raise HTTPException(422, 'Posisi legend tidak tersedia')
    if not 0 <= panel.get('decimals', 2) <= 4:
        raise HTTPException(422, 'Desimal harus 0-4')
    target = panel.get('display_unit')
    if target:
        if panel['source'] != 'metric' or target not in unit_specs or not unit_specs[target].active:
            raise HTTPException(422, 'Konversi tampilan hanya tersedia untuk parameter pengukuran')
        for code in panel['metric_codes']:
            source = metric_units[code]
            if source not in unit_specs or unit_specs[source].dimension != unit_specs[target].dimension:
                raise HTTPException(422, 'Satuan tampilan tidak kompatibel dengan parameter')
    if pair and panel['kind'] == 'stacked_bar' and set(pair).issubset(panel['metric_codes']):
        raise HTTPException(422, 'Daya mampu dan beban sistem tidak boleh ditumpuk menjadi satu total')
