"""Compact authorized map endpoint and admin-only tile settings."""
import re
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import UnitContext, unit_context
from .analysis_router import AnalysisOptions, options_with_findings, validate_options
from .common import audit, dump, require_admin
from .map_models import DEFAULT_TILES, GarduTileSettings
from .map_service import map_points

router = APIRouter(prefix='/api/substations/map', tags=['Gardu Map'])
TILES = re.compile(r'^\{[sxyz]\}$')


class TileUpdate(BaseModel):
    enabled: bool
    tile_url: str = Field(max_length=350)
    attribution: str = Field(max_length=400)


def check_tile_settings(body):
    url = body.tile_url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.netloc or parts.username or parts.password:
        raise HTTPException(422, 'URL ubin hanya boleh http/https dengan host sah')
    if any(x not in url for x in ('{z}', '{x}', '{y}')):
        raise HTTPException(422, 'URL ubin wajib memakai {z}, {x}, dan {y}')
    if len(url) > 350 or len(url) < 20 or re.search(r'[\s<>"\x00-\x1f]', url):
        raise HTTPException(422, 'URL ubin mengandung karakter tidak sah')
    if not body.attribution.strip() or any(c in body.attribution for c in '<>'):
        raise HTTPException(422, 'Atribusi harus teks biasa yang tidak kosong')
    return url


@router.get('/tiles')
def tile_settings(db: Session = Depends(get_db),
                  ctx: UnitContext = Depends(unit_context('read'))):
    row = db.get(GarduTileSettings, 1)
    return dump(row) if row else dict(DEFAULT_TILES)


@router.patch('/tiles')
def set_tiles(body: TileUpdate, db: Session = Depends(get_db),
              ctx: UnitContext = Depends(unit_context('read'))):
    require_admin(ctx)
    url = check_tile_settings(body)
    row = db.get(GarduTileSettings, 1)
    before = dump(row) if row else None
    if row is None:
        row = GarduTileSettings(id=1)
        db.add(row)
    row.enabled = body.enabled
    row.tile_url = url
    row.attribution = body.attribution.strip()
    db.flush()
    audit(db, ctx, 'gardu_tiles', 1, before, dump(row))
    db.commit()
    return dump(row)


@router.get('/points')
def points(opt: AnalysisOptions = Depends(options_with_findings),
           color_column: str | None = Query(None, max_length=60),
           db: Session = Depends(get_db),
           ctx: UnitContext = Depends(unit_context('read'))):
    validate_options(db, opt)
    return map_points(db, ctx, opt, color_column)
