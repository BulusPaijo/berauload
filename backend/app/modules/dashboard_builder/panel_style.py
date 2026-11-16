"""Whitelisted panel presentation settings. No arbitrary CSS is accepted."""
import re
from fastapi import HTTPException

HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
PRESETS = {'classic', 'dark', 'soft'}
FONTS = {'system', 'mono'}


def validate_panel_style(panel: dict):
    if panel.get('style_preset', 'classic') not in PRESETS:
        raise HTTPException(422, 'Preset tampilan panel tidak dikenal')
    if panel.get('font_family', 'system') not in FONTS:
        raise HTTPException(422, 'Font panel tidak didukung')
    if not 11 <= panel.get('title_font_size', 13) <= 24:
        raise HTTPException(422, 'Ukuran judul panel 11–24 px')
    if not 18 <= panel.get('value_font_size', 32) <= 54:
        raise HTTPException(422, 'Ukuran angka panel 18–54 px')
    for key in ('text_color', 'background_color', 'border_color'):
        value = panel.get(key)
        if value is not None and not HEX.fullmatch(value):
            raise HTTPException(422, 'Kode warna panel harus #RRGGBB')
