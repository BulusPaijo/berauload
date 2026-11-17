"""Stage 3 modular route extraction; legacy URL and behavior preserved."""
import io
from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ...db import Metric, Reading, HourRecord, get_db
from ..org_units.models import UnitDayState
from ..branding.service import current as branding_current, slug as brand_slug, sheet_title, pdf_logo
from ..org_units.context import UnitContext, unit_context
from ...security import current_user
from ..analytics_core.router import load_analytics
from ..org_units.repository import home_unit as org_home
from ..org_units.roles import metric_for_role, SYSTEM_LOAD
router = APIRouter(prefix='/api', tags=['Legacy Reports'])

@router.get('/reports/export')
def export_report(start:date,end:date,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    if start>end or (end-start).days>366:raise HTTPException(422,'Export maksimal 367 hari')
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill,Alignment
    from openpyxl.utils import get_column_letter
    wb=Workbook();ws=wb.active;brand=branding_current(db)
    ws.title='Pembacaan Per Jam' if brand['app_short_name']=='BerauLoad' else sheet_title(brand['app_short_name'])
    metrics=db.query(Metric).filter_by(active=True,unit_id=ctx.id).order_by(Metric.display_order).all()
    metric_by_id={m.id:m for m in metrics}
    heads=['Tanggal (WITA)','Jam (WITA)','Status']+[m.name+' ('+m.unit+')' for m in metrics]
    ws.append(heads)
    data=(db.query(HourRecord.day,HourRecord.hour,Reading.metric_id,Reading.value)
          .join(Reading,Reading.hour_id==HourRecord.id)
          .filter(HourRecord.day>=start,HourRecord.day<=end,Reading.metric_id.in_(metric_by_id))
          .order_by(HourRecord.day,HourRecord.hour).all())
    recordmap=defaultdict(dict)
    for d,h,mid,v in data:recordmap[(d,h)][mid]=float(v)
    statuses={r.day:r.status for r in db.query(UnitDayState).filter(UnitDayState.unit_id==ctx.id,UnitDayState.day>=start,UnitDayState.day<=end).all()}
    for (d,h),v in sorted(recordmap.items()):
        ws.append([d.isoformat(),f'{h:02d}:00',statuses.get(d,'draft')]+[v.get(m.id) for m in metrics])
    ws.freeze_panes='D2';ws.auto_filter.ref=ws.dimensions
    for cell in ws[1]:cell.fill=PatternFill('solid',fgColor='143B52');cell.font=Font(color='FFFFFF',bold=True)
    for col in range(1,len(heads)+1):ws.column_dimensions[get_column_letter(col)].width=21 if col>3 else 18
    # Separate normalized daily summary, calculated from actual available readings.
    sh=wb.create_sheet('Rekap Harian');sh.append(['Tanggal','Beban Puncak (kW)','Rata-rata (kW)','Beban Min (kW)','Jam Tercatat','Kelengkapan (%)'])
    load=metric_for_role(db,ctx.id,SYSTEM_LOAD)
    daily=load_analytics(db,load.code,'day',start,end,ctx.id)['data'] if load else []
    for r in daily:sh.append([r['period'],r['peak'],r['avg'],r['min'],r['count'],round(r['count']/24*100,2)])
    sh.freeze_panes='B2'
    for cell in sh[1]:cell.fill=PatternFill('solid',fgColor='143B52');cell.font=Font(color='FFFFFF',bold=True)
    for c in 'ABCDEF':sh.column_dimensions[c].width=23
    out=io.BytesIO();wb.save(out);out.seek(0)
    return StreamingResponse(out,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
           headers={'Content-Disposition':f'attachment; filename="{brand_slug(brand["app_short_name"])}_{start}_{end}.xlsx"'})

@router.get('/reports/pdf')
def pdf_report(start:date,end:date,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    if start>end or (end-start).days>366:raise HTTPException(422,'Laporan maksimal 367 hari')
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    load=metric_for_role(db,ctx.id,SYSTEM_LOAD)
    rows=load_analytics(db,load.code,'day',start,end,ctx.id)['data'] if load else []
    brand=branding_current(db)
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=38,leftMargin=38,topMargin=45,bottomMargin=45,
                          title=f'{brand["app_name"]} - Laporan Beban Sistem Berau')
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle('titleBerau',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=16,
                               textColor=colors.HexColor('#143B52'),alignment=TA_CENTER,spaceAfter=9)
    body_style=ParagraphStyle('detailBerau',parent=styles['Normal'],fontSize=9,leading=14,
                              textColor=colors.HexColor('#395968'))
    from xml.sax.saxutils import escape
    title = ('LAPORAN BEBAN SISTEM KELISTRIKAN BERAU' if brand['app_name']=='BerauLoad'
             else f'LAPORAN BEBAN SISTEM - {brand["app_name"]}')
    story=[Paragraph(escape(title),title_style),
           Paragraph(f'Periode: {start} s.d. {end} | Zona waktu: WITA (UTC+08:00)',body_style),
           Paragraph(f'Sumber: pembacaan historis {escape(brand["app_name"])}. Nilai kosong tidak dianggap nol.',body_style),
           Spacer(1,16)]
    if brand['organization_name']:
        story.insert(1, Paragraph(escape(brand['organization_name']), body_style))
    logo = pdf_logo(brand)
    if logo is not None:
        story.insert(0, logo)
    vals=[r['peak'] for r in rows]
    story.append(Paragraph(f'Hari memiliki data: {len(rows)} | Puncak tertinggi: {max(vals):,.2f} kW' if vals else
                           'Belum ada data pengukuran untuk periode terpilih.',body_style))
    story.append(Spacer(1,10))
    table_data=[['Tanggal','Minimum kW','Rata-rata kW','Puncak kW','Jam','Cakupan']]
    for r in rows:
        table_data.append([r['period'],f"{r['min']:,.2f}",f"{r['avg']:,.2f}",f"{r['peak']:,.2f}",
                           str(r['count']),f"{r['count']/24*100:.0f}%"])
    if len(table_data)>1:
        table=Table(table_data,colWidths=[87,106,106,106,54,58],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#143B52')),
                       ('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                       ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8),
                       ('BOTTOMPADDING',(0,0),(-1,0),10),('TOPPADDING',(0,0),(-1,0),10),
                       ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),
                       ('LINEBELOW',(0,0),(-1,-1),0.3,colors.HexColor('#e4ebee')),
                       ('ALIGN',(1,1),(-1,-1),'RIGHT'),('BOTTOMPADDING',(0,1),(-1,-1),7),
                       ('TOPPADDING',(0,1),(-1,-1),7)]))
        story.append(table)
    story.extend([Spacer(1,16),Paragraph('Catatan: rata-rata dihitung dari jam yang benar-benar tercatat. '
                  'Bulan/hari parsial tidak direkayasa menjadi data lengkap. Laporan ini bukan telemetry real-time.',body_style)])
    doc.build(story);buffer.seek(0)
    return StreamingResponse(buffer,media_type='application/pdf',
           headers={'Content-Disposition':f'attachment; filename="{brand_slug(brand["app_short_name"])}_{start}_{end}.pdf"'})
