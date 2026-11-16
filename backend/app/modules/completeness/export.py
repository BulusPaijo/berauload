"""Temporary XLSX response, using the application's existing spreadsheet dependency."""
import os
import tempfile
from pathlib import Path
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from ..data_export.service import safe_spreadsheet_text


def text_cell(value):
    return safe_spreadsheet_text(str(value))


def save_workbook(data):
    fd, path = tempfile.mkstemp(prefix='berauload_completeness_', suffix='.xlsx')
    os.close(fd)
    try:
        workbook = Workbook()
        matrix = workbook.active
        matrix.title = 'Kelengkapan Harian'
        matrix.append(['Unit', 'Dasar', *data['dates'], 'Kelengkapan', 'Hari Final'])
        matrix.freeze_panes = 'C2'
        for row in data['rows']:
            label = '   ' * row['depth'] + row['unit_name']
            matrix.append([text_cell(label), text_cell(row['basis']),
                           *[f"{v['filled_hours']}/{v['expected_hours']} ({v['status'][0].upper()})" +
                             (' future' if v['future'] else '') for v in row['days']],
                           row['summary']['percent'], row['summary']['final_days']])
        matrix.append(['KESELURUHAN', '', *['' for _ in data['dates']],
                       data['summary']['percent'], data['summary']['final_days']])
        summary = workbook.create_sheet('Ringkasan dan Dasar')
        summary.append(['Unit', 'Basis', 'Jam terisi', 'Jam diharapkan', '%', 'Hari final'])
        for row in data['rows']:
            s = row['summary']
            summary.append([text_cell(row['unit_name']), text_cell(row['basis']),
                            s['filled_hours'], s['expected_hours'], s['percent'], s['final_days']])
        s = data['summary']
        summary.append(['KESELURUHAN', '', s['filled_hours'], s['expected_hours'],
                        s['percent'], s['final_days']])
        summary.append(['system.load', 'Pembacaan non-NULL pada parameter peran system.load'])
        summary.append(['any_input', 'Minimal satu parameter input aktif dengan pembacaan'])
        summary.append(['Jam sekarang', 'Jam yang sedang berlangsung dihitung mulai awal jam WITA'])
        for sheet in workbook:
            for cell in sheet[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill('solid', fgColor='173C53')
            sheet.column_dimensions['A'].width = 36
            sheet.column_dimensions['B'].width = 28
        workbook.save(path)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise


def response(data):
    path = save_workbook(data)
    return FileResponse(path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        filename=f"berauload_kelengkapan_{data['start']}_{data['end']}.xlsx",
                        background=BackgroundTask(Path(path).unlink, missing_ok=True))
