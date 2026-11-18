"""Admin-managed basemap. Measurements and derived values remain untouched."""
from sqlalchemy import Boolean, Column, Integer, String
from ...db import Base


class GarduTileSettings(Base):
    __tablename__ = 'gardu_tile_settings'
    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    tile_url = Column(String(350), nullable=False)
    attribution = Column(String(400), nullable=False)


DEFAULT_TILES = {
    'enabled': True,
    'tile_url': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'attribution': '© OpenStreetMap contributors',
}
