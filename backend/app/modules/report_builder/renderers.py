"""Render report layouts as PDFs or workbooks without executing user-supplied text."""
from __future__ import annotations
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Line, String
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from ..data_export.service import safe_spreadsheet_text
from ..branding.service import pdf_logo, sheet_title


def _fmt(value):
    return '—' if value is None else f'{value:,.2f}'


def _chart(block):
    rows, codes = block.get('rows') or [], block['metric_codes']
    drawing = Drawing(690, 190)
    if not rows:
        drawing.add(String(12, 90, 'Belum ada data untuk periode ini', fontSize=11))
        return drawing
    graph = [(i, c, float(row[c])) for i, row in enumerate(rows)
             for c in codes if isinstance(row.get(c), (int, float))]
    if not graph:
        drawing.add(String(12, 90, 'Belum ada nilai valid', fontSize=11))
        return drawing
    low, high = min(v for _, _, v in graph), max(v for _, _, v in graph)
    margin = (high-low)*0.12 if high != low else max(abs(high)*0.12, 1.0)
    lo, hi = low-margin, high+margin
    x0, y0, width, height = 48, 24, 622, 146
    drawing.add(Line(x0, y0, x0, y0+height, strokeColor=colors.grey))
    drawing.add(Line(x0, y0, x0+width, y0, strokeColor=colors.grey))
    palette = [colors.HexColor('#087f8c'), colors.HexColor('#e78538')]
    for k, code in enumerate(codes):
        for i in range(1, len(rows)):
            a, b = rows[i-1].get(code), rows[i].get(code)
            if a is None or b is None:
                continue  # Preserve missing intervals as gaps.
            xa = x0+width*(i-1)/max(len(rows)-1, 1)
            xb = x0+width*i/max(len(rows)-1, 1)
            ya = y0+height*(float(a)-lo)/(hi-lo)
            yb = y0+height*(float(b)-lo)/(hi-lo)
            drawing.add(Line(xa, ya, xb, yb, strokeColor=palette[k], strokeWidth=1.8))
        drawing.add(String(x0+k*240, 180, code[:40], fontSize=8, fillColor=palette[k]))
    drawing.add(String(3, y0, _fmt(lo), fontSize=7))
    drawing.add(String(3, y0+height, _fmt(hi), fontSize=7))
    drawing.add(String(x0, 8, rows[0]['period'][:22], fontSize=7))
    drawing.add(String(x0+width-115, 8, rows[-1]['period'][:22], fontSize=7))
    return drawing


def render_pdf(name: str, data: dict, branding=None) -> bytes:
    memory = BytesIO()
    doc = SimpleDocTemplate(memory, pagesize=landscape(A4), leftMargin=48,
                            rightMargin=48, topMargin=46, bottomMargin=46)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Title'],
                              fontSize=18, textColor=colors.HexColor('#153d52')))
    styles.add(ParagraphStyle(name='ReportNote', parent=styles['Normal'],
                              fontSize=8, textColor=colors.HexColor('#647e8c')))
    elements = [Paragraph(escape(name), styles['ReportTitle']),
                Paragraph(f'Periode: {data["start"]} s.d. {data["end"]} | WITA', styles['ReportNote']),
                Spacer(1, 20)]
    if branding:
        if branding.get('organization_name'):
            elements.insert(1, Paragraph(escape(branding['organization_name']), styles['ReportNote']))
        logo = pdf_logo(branding)
        if logo is not None:
            elements.insert(0, logo)
    for block in data['blocks']:
        title = Paragraph(escape(block['title']), styles['Heading2'])
        if block['kind'] == 'heading':
            elements.extend([title, Spacer(1, 12)])
        elif block['kind'] == 'text':
            elements.extend([title, Paragraph(escape(block['text']).replace('\n', '<br/>'),
                                            styles['Normal']), Spacer(1, 12)])
        elif block['kind'] == 'stat':
            elements.extend([title, Paragraph(f'<b>{_fmt(block["value"])} {escape(block["unit"])}</b>'
                                            f' ({block["count"]} pembacaan)', styles['Normal']), Spacer(1, 14)])
        elif block['kind'] == 'chart':
            elements.extend([title, _chart(block), Spacer(1, 15)])
        else:
            header = ['Periode'] + [escape(code) for code in block['metric_codes']]
            rows = [[r['period']] + [_fmt(r.get(c)) for c in block['metric_codes']]
                    for r in block.get('rows', [])][:120]
            table = Table([header] + rows, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f1f3')),
                                       ('GRID', (0, 0), (-1, -1), .25, colors.lightgrey),
                                       ('FONTSIZE', (0, 0), (-1, -1), 8),
                                       ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                                       ('TOPPADDING', (0, 0), (-1, -1), 7)]))
            elements.extend([title, table])
            if len(block.get('rows', [])) > 120:
                elements.append(Paragraph('PDF hanya memuat 120 baris pertama tabel ini. '
                                          'Gunakan ekspor Excel untuk seluruh baris periode.',
                                          styles['ReportNote']))
            elements.append(Spacer(1, 14))
    elements.append(Paragraph(f'Sumber: {escape(branding["app_name"] if branding else "BerauLoad")}. Data kosong tidak diperlakukan sebagai nol.',
                              styles['ReportNote']))
    doc.build(elements)
    return memory.getvalue()


def render_xlsx(name: str, data: dict, branding=None) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title(branding['app_short_name']) if branding and branding['app_short_name']!='BerauLoad' else 'Laporan'
    sheet.append([safe_spreadsheet_text(name)])
    sheet.append([f'Periode {data["start"]} s.d. {data["end"]} (WITA)'])
    sheet.append([])
    for b in data['blocks']:
        sheet.append([safe_spreadsheet_text(b['title'])])
        if b['kind'] == 'text':
            sheet.append([safe_spreadsheet_text(b['text'])])
        elif b['kind'] == 'stat':
            sheet.append(['Nilai', b['value'], b['unit'], 'Pembacaan', b['count']])
        elif b['kind'] in {'chart', 'table'}:
            sheet.append(['Periode'] + b['metric_codes'])
            for row in b.get('rows', []):
                sheet.append([safe_spreadsheet_text(row['period'])] + [row.get(c) for c in b['metric_codes']])
        sheet.append([])
    sheet.column_dimensions['A'].width = 34
    for col in 'BCDE':
        sheet.column_dimensions[col].width = 22
    for row in sheet:
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
    sheet['A1'].font = Font(bold=True, size=17, color='137F8A')
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
