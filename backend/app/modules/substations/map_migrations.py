"""Schema-only, additive and restart-idempotent Stage 9d-1 migration."""
from sqlalchemy import select
from ..formulas.models import SchemaMigration
from .map_models import DEFAULT_TILES, GarduTileSettings

VERSION = '20261117_20_stage9d1_tiles'


def run(engine):
    with engine.begin() as conn:
        SchemaMigration.__table__.create(conn, checkfirst=True)
        GarduTileSettings.__table__.create(conn, checkfirst=True)
        already = conn.execute(select(SchemaMigration.version).where(
            SchemaMigration.version == VERSION)).first()
        if already:
            return
        if not conn.execute(select(GarduTileSettings.id).where(
                GarduTileSettings.id == 1)).first():
            conn.execute(GarduTileSettings.__table__.insert().values(
                id=1, **DEFAULT_TILES))
        conn.execute(SchemaMigration.__table__.insert().values(version=VERSION))
