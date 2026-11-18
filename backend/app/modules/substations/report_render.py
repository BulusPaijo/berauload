"""Stage 9d-3 report and field-worksheet rendering (XLSX via openpyxl, PDF via reportlab)."""
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from .analysis_export import clean
from .report_data import FOLLOW_HEAD, LATE_HEAD, LIST_HEAD, late_rows

BOLD = Font(bold=True)
GREY = PatternFill('solid', fgColor='E6ECEF')


def _stamp():
    return datetime.now(ZoneInfo('Asia/Makassar')).strftime('%d-%m-%Y %H:%M WITA')


def _sheet(wb, title, head, rows):
    ws = wb.create_sheet(title[:31])
    ws.append(head)
    for c in ws[1]:
        c.font = BOLD
    for r in rows:
        ws.append([None if v is None else clean(v) for v in r])
    for i, h in enumerate(head, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = max(10, min(40, len(h) + 6))
    return ws


def report_xlsx(data, brand, period):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Ringkasan'
    ws.append([brand['organization_name'] or brand['app_name']]); ws['A1'].font = Font(bold=True, size=13)
    ws.append(['Laporan Pengukuran Gardu', period]); ws.append(['Dibuat', _stamp()]); ws.append([])
    ws.append(['Total gardu (filter)', data['summary']['total']])
    ws.append(['Kategori', 'Jumlah gardu'])
    for c in data['summary']['categories']:
        ws.append([c['name'], c['count']])
    ws.append(['Tidak dapat dinilai', data['summary']['unassessed']]); ws.append([])
    ws.append(['Temuan', 'Jumlah gardu'])
    for f in data['summary']['findings']:
        ws.append([f['name'], f['count']])
    ws.append([]); ws.append([f'Belum diukur > {data["stale_days"]} hari', data['unmeasured']['total']])
    ws.append(['Tindak lanjut terbuka/dikerjakan', len(data['followups'])])
    ws.column_dimensions['A'].width = 36
    for s in data['sections']:
        _sheet(wb, s['title'].replace(':', ' -'), LIST_HEAD, s['rows'])
    _sheet(wb, 'Belum diukur', LATE_HEAD, late_rows(data))
    _sheet(wb, 'Tindak lanjut', FOLLOW_HEAD, data['followups'])
    _sheet(wb, 'Ambang dipakai', ['Jenis', 'Nama', 'Syarat'], data['rules'])
    out = io.BytesIO(); wb.save(out)
    return out.getvalue()


def _table(rows, widths=None, head=True):
    t = Table([[('' if v is None else str(v)) for v in r] for r in rows], colWidths=widths, repeatRows=1 if head else 0)
    style = [('FONT', (0, 0), (-1, -1), 'Helvetica', 7.5), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#C9D6DC')),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
    if head:
        style += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E3EFF1')), ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 7.5)]
    t.setStyle(TableStyle(style))
    return t


def _doc(story_fn, brand, title, period, logo):
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=title)
    st = getSampleStyleSheet()
    head = [Paragraph(f"<b>{brand['organization_name'] or brand['app_name']}</b>", st['Normal']),
            Paragraph(f'<font size=14><b>{title}</b></font>', st['Normal']),
            Paragraph(f'{period} · dibuat {_stamp()}', st['Normal'])]
    top = Table([[logo or '', head]], colWidths=[60, None]) if logo else Table([[head]])
    story = [top, Spacer(1, 6)] + story_fn(st)
    doc.build(story)
    return out.getvalue()


def report_pdf(data, brand, period, logo):
    def story(st):
        s = data['summary']
        cats = [['Kategori', 'Gardu']] + [[c['name'], c['count']] for c in s['categories']] + [['Tidak dapat dinilai', s['unassessed']]]
        finds = [['Temuan', 'Gardu']] + [[f['name'], f['count']] for f in s['findings']]
        out = [Paragraph(f"Total gardu sesuai filter: <b>{s['total']}</b> · belum diukur &gt; {data['stale_days']} hari: "
                         f"<b>{data['unmeasured']['total']}</b> · tindak lanjut terbuka: <b>{len(data['followups'])}</b>", st['Normal']),
               Spacer(1, 6), Table([[_table(cats, [120, 50]), _table(finds, [160, 50])]], hAlign='LEFT'), Spacer(1, 8)]
        for sec in data['sections']:
            out += [Paragraph(f"<b>{sec['title']}</b> — {sec['total']} gardu (syarat: {sec['rule']})", st['Normal']),
                    _table([LIST_HEAD] + sec['rows'], [55, 140, 60, 40, 55, 60, 250]), Spacer(1, 6)]
        out += [PageBreak(), Paragraph(f"<b>Belum diukur &gt; {data['stale_days']} hari</b> ({data['unmeasured']['total']})", st['Normal']),
                _table([LATE_HEAD] + late_rows(data)[:120], [60, 180, 80, 50, 80, 60]), Spacer(1, 8),
                Paragraph('<b>Tindak lanjut terbuka / dikerjakan</b>', st['Normal']),
                _table([FOLLOW_HEAD] + data['followups'], [55, 120, 100, 50, 60, 90, 55, 200]), Spacer(1, 8),
                Paragraph('<b>Ambang yang dipakai</b> (ditetapkan admin; sel kosong berarti tidak ada nilai, bukan nol)', st['Normal']),
                _table([['Jenis', 'Nama', 'Syarat']] + [list(r) for r in data['rules']], [60, 150, 450])]
        return out
    return _doc(story, brand, 'Laporan Pengukuran Gardu', period, logo)


def worksheet_xlsx(stations, layout, feeders):
    groups, station_params = layout
    wb = Workbook(); ws = wb.active; ws.title = 'Lembar kerja'
    head = ['Kode', 'Nama', 'Alamat', 'Penyulang', 'kVA', 'Koordinat', 'Jurusan']
    for unit, labels, _ in groups:
        head += [f'{lab} ({unit})' for lab in labels]
    ws.append(['Tanggal:', '', 'Sesi:', '', 'Petugas:']); ws.append(head)
    for c in ws[2]:
        c.font = BOLD
    for s in stations:
        for line in range(1, s.line_count + 1):
            ws.append([s.code, s.name, s.address, feeders.get(s.feeder_id), float(s.power_kva),
                       f'{s.lat},{s.lon}' if s.lat is not None else None, line])
        for name, unit in station_params:
            ws.append([s.code, s.name, None, None, None, None, f'{name} ({unit})'])
            ws.cell(ws.max_row, 7).fill = GREY
    out = io.BytesIO(); wb.save(out)
    return out.getvalue()


def worksheet_pdf(stations, layout, feeders, brand, logo):
    groups, station_params = layout

    def story(st):
        out = [Paragraph('Tanggal: ____________   Sesi: ____________   Petugas: ______________________', st['Normal']), Spacer(1, 6)]
        for s in stations:
            ident = f"<b>{s.code}</b> — {s.name} · {s.address or '-'} · {feeders.get(s.feeder_id) or '-'} · " \
                    f"{float(s.power_kva):g} kVA · {s.line_count} jurusan" + (f' · {s.lat},{s.lon}' if s.lat is not None else '')
            head = ['Jurusan'] + [f'{lab} ({unit})' for unit, labels, _ in groups for lab in labels]
            rows = [head] + [[str(n)] + [''] * (len(head) - 1) for n in range(1, s.line_count + 1)]
            extra = [[f'{n} ({u})', ''] for n, u in station_params]
            out += [Paragraph(ident, st['Normal']), _table(rows), Spacer(1, 3)]
            if extra:
                out += [_table([['Parameter gardu', 'Nilai']] + extra, [160, 80])]
            out += [Spacer(1, 10)]
        return out
    return _doc(story, brand, 'Lembar Kerja Pengukuran Gardu', f'{len(stations)} gardu', logo)
