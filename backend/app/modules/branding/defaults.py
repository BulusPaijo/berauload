"""Authoritative display defaults; frontend copy checked by tests."""
DEFAULTS = {
    'app_name': 'BerauLoad',
    'app_short_name': 'BerauLoad',
    'tagline': 'Sistem Kelistrikan Berau',
    'login_eyebrow': 'SISTEM KELISTRIKAN BERAU',
    'login_welcome': 'Selamat datang di',
    'login_description': 'Pencatatan operasional, monitoring dan analisis beban dalam satu platform.',
    'login_button_text': 'Masuk ke BerauLoad',
    'login_footnote': 'Akses khusus untuk personel yang berwenang.',
    'organization_name': '',
    'footer_text': 'Data operasional internal',
    'color_primary': '#087E89',
    'color_accent': '#03A7A4',
}
TEXT_LIMITS = dict(app_name=40, app_short_name=20, tagline=60,
                   login_eyebrow=80, login_welcome=80,
                   login_description=200, login_button_text=60,
                   login_footnote=120, organization_name=100, footer_text=120)
FIELDS = tuple(DEFAULTS)
