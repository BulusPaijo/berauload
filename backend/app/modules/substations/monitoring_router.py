"""Stage 9d-3 monitoring + reports API (read-only; uses Analisa filter as single source)."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import get_db
from ..branding.service import current as brand_current, pdf_logo, slug
from ..org_units.context import UnitContext, unit_context
from .analysis_router import AnalysisOptions, options_with_findings, validate_options
from .common import audit, child_ids
from .models import Substation, SubstationFeeder
from .monitoring_service import coverage, today, unmeasured
from .report_data import report_data, worksheet_layout
from .report_render import report_pdf, report_xlsx, worksheet_pdf, worksheet_xlsx

router = APIRouter(prefix='/api/substations/monitoring', tags=['Gardu Monitoring'])
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@router.get('/coverage')
def get_coverage(start: date | None = None, end: date | None = None, db: Session = Depends(get_db),
                 ctx: UnitContext = Depends(unit_context('read'))):
    end = end or today()
    start = start or end - timedelta(days=90)
    if start > end or (end - start).days > 3660:
        raise HTTPException(422, 'Rentang tanggal tidak sah (maksimal 10 tahun)')
    return coverage(db, ctx, start, end)


@router.get('/unmeasured')
def get_unmeasured(days: int | None = Query(None, ge=0, le=3650), feeder_id: int | None = None,
                   text: str = Query('', max_length=120), page: int = Query(1, ge=1),
                   page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
                   ctx: UnitContext = Depends(unit_context('read'))):
    from .monitoring_service import stale_days
    return unmeasured(db, ctx, stale_days(db) if days is None else days, feeder_id, text, page, page_size)


def _file(data, name, fmt):
    return Response(data, media_type=XLSX if fmt == 'xlsx' else 'application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{name}.{fmt}"'})


@router.get('/report')
def report(format: str = 'pdf', opt: AnalysisOptions = Depends(options_with_findings),
           db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    if format not in ('pdf', 'xlsx'):
        raise HTTPException(422, 'Format laporan harus pdf atau xlsx')
    validate_options(db, opt)
    data = report_data(db, ctx, opt)
    brand = brand_current(db)
    period = (f'{opt.start} s.d. {opt.end}' if opt.mode != 'terakhir' and opt.start and opt.end
              else 'Pengukuran terakhir tiap gardu') + f' · {ctx.unit.name}'
    body = report_xlsx(data, brand, period) if format == 'xlsx' else report_pdf(data, brand, period, pdf_logo(brand))
    audit(db, ctx, 'gardu_report', 0, after={'format': format, 'filter': opt.model_dump(mode='json')})
    db.commit()
    return _file(body, f"{slug(brand['app_short_name'])}_Laporan_Gardu_{today():%Y%m%d}", format)


class WorksheetBody(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=300)
    format: str = 'pdf'


@router.post('/worksheet')
def worksheet(body: WorksheetBody, db: Session = Depends(get_db), ctx: UnitContext = Depends(unit_context('read'))):
    if body.format not in ('pdf', 'xlsx'):
        raise HTTPException(422, 'Format lembar kerja harus pdf atau xlsx')
    allowed = child_ids(db, ctx)
    stations = db.query(Substation).filter(Substation.id.in_(body.ids), Substation.unit_id.in_(allowed)).order_by(Substation.code).all()
    if len(stations) != len(set(body.ids)):
        raise HTTPException(404, 'Sebagian gardu tidak ditemukan pada unit yang berhak')
    feeders = {f.id: f.name for f in db.query(SubstationFeeder.id, SubstationFeeder.name)}
    layout = worksheet_layout(db)
    brand = brand_current(db)
    data = worksheet_xlsx(stations, layout, feeders) if body.format == 'xlsx' else worksheet_pdf(stations, layout, feeders, brand, pdf_logo(brand))
    return _file(data, f"{slug(brand['app_short_name'])}_Lembar_Kerja_Gardu", body.format)
