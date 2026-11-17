"""Stream CSV/XLSX into temporary files, avoiding large in-memory workbooks."""
import csv
import os
import tempfile
from pathlib import Path
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill
from .service import safe_spreadsheet_text
from ..branding.service import sheet_title


def render_file(headings, rows, fmt, branding=None):
    fd, path = tempfile.mkstemp(prefix='berauload_export_', suffix='.' + fmt)
    os.close(fd)
    try:
        if fmt == 'csv':
            with open(path, 'w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                writer.writerow([safe_spreadsheet_text(x) for x in headings])
                for row in rows:
                    writer.writerow([safe_spreadsheet_text(x) if x is not None else '' for x in row])
        else:
            wb = Workbook(write_only=True)
            ws = wb.create_sheet(sheet_title(branding['app_short_name'] if branding else 'BerauLoad'))
            ws.freeze_panes = 'B2'
            titles = []
            for heading in headings:
                cell = WriteOnlyCell(ws, value=safe_spreadsheet_text(heading))
                cell.font = Font(color='FFFFFF', bold=True)
                cell.fill = PatternFill('solid', fgColor='143B52')
                titles.append(cell)
            ws.append(titles)
            for row in rows:
                ws.append([safe_spreadsheet_text(x) for x in row])
            wb.save(path)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
