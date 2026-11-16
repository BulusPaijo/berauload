"""Additive, repeatable schema migration; never alters measurement columns."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .models import InputFormTab, InputFormPlacement, InputFormRevision

VERSION = '20261114_03_dynamic_input_form'
DEFAULT_TABS = (
    ('PEMBANGKIT', 'Pembangkit'),
    ('KUALITAS', 'Frekuensi & Tegangan'),
    ('FEEDER', 'Arus Feeder'),
    ('REKAP', 'Rekap Sistem'),
    ('REKAP_LAIN', 'Kolom Rekap Tambahan'),
)


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        for model in (InputFormTab, InputFormPlacement, InputFormRevision):
            model.__table__.create(conn, checkfirst=True)
        present = set(conn.execute(select(InputFormTab.code)).scalars())
        for order, (code, name) in enumerate(DEFAULT_TABS):
            if code not in present:
                conn.execute(InputFormTab.__table__.insert().values(
                    code=code, name=name, display_order=order, active=True))
        if not conn.execute(select(InputFormRevision.id).where(InputFormRevision.id == 1)).first():
            conn.execute(InputFormRevision.__table__.insert().values(id=1, version=1))
        if not conn.execute(select(SchemaMigration.version).where(
                SchemaMigration.version == VERSION)).first():
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
