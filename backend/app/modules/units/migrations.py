"""Additive, repeatable unit registry migration; original Metric.unit stays unchanged."""
from decimal import Decimal
from sqlalchemy import select
from ...db import Metric
from ..formulas.models import SchemaMigration
from .models import UnitDefinition

VERSION = '20261114_04_master_satuan'
# code, name, dimension, factor to dimension base; % uses 0.01 only for display conversion.
SEED = (
    ('W', 'Watt', 'active_power', '0.001'), ('kW', 'Kilowatt', 'active_power', '1'),
    ('MW', 'Megawatt', 'active_power', '1000'),
    ('VA', 'Volt-ampere', 'apparent_power', '0.001'),
    ('kVA', 'Kilovolt-ampere', 'apparent_power', '1'),
    ('MVA', 'Megavolt-ampere', 'apparent_power', '1000'),
    ('Wh', 'Watt-hour', 'active_energy', '0.001'),
    ('kWh', 'Kilowatt-hour', 'active_energy', '1'),
    ('MWh', 'Megawatt-hour', 'active_energy', '1000'),
    ('V', 'Volt', 'voltage', '0.001'), ('kV', 'Kilovolt', 'voltage', '1'),
    ('A', 'Ampere', 'current', '1'), ('kA', 'Kiloampere', 'current', '1000'),
    ('Hz', 'Hertz', 'frequency', '1'), ('kHz', 'Kilohertz', 'frequency', '1000'),
    ('kVAr', 'Kilovolt-ampere reaktif', 'reactive_power', '1'),
    ('MVAr', 'Megavolt-ampere reaktif', 'reactive_power', '1000'),
    ('kVArh', 'Energi reaktif', 'reactive_energy', '1'),
    ('%', 'Persen', 'ratio', '0.01'), ('1', 'Tanpa satuan', 'ratio', '1'),
    ('—', 'Satuan belum ditentukan (legacy)', 'unspecified', '1'),
)


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        UnitDefinition.__table__.create(conn, checkfirst=True)
        present = set(conn.execute(select(UnitDefinition.code)).scalars())
        for code, name, dimension, factor in SEED:
            if code not in present:
                conn.execute(UnitDefinition.__table__.insert().values(
                    code=code, name=name, dimension=dimension,
                    factor=Decimal(factor), active=True, builtin=True))
                present.add(code)
        for code in conn.execute(select(Metric.unit).distinct()).scalars():
            if code and code not in present:
                conn.execute(UnitDefinition.__table__.insert().values(
                    code=code, name=f'Legacy {code}', dimension=f'legacy_{code}'[:40],
                    factor=Decimal('1'), active=True, builtin=False))
                present.add(code)
        if not conn.execute(select(SchemaMigration.version).where(SchemaMigration.version == VERSION)).first():
            conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
