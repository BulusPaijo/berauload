"""Spreadsheet template structure. All user-editable cells start at C4."""
from datetime import timedelta, datetime, timezone
import re
import tempfile
from openpyxl import Workbook
from openpyxl.styles import Protection, PatternFill, Font, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from .repository import eligible_tabs

TEMPLATE_VERSION = '1'
DATE_FORMAT = 'yyyy-mm-dd'
INVALID_SHEET = re.compile(r'[\\/*?:\[\]]')


def excel_text(value):
    """Keep administrative labels as text, never executable Excel expressions."""
    raw = str(value)
    return "'" + raw if raw.startswith(('=', '+', '-', '@', '\t', '\r')) else raw


def safe_sheet_name(name, used):
    title = INVALID_SHEET.sub('_', str(name).replace('\n', ' ')).strip("' ") or 'Form'
    title = title[:31]
    original = title
    suffix = 2
    while title.casefold() in used or title.casefold() in {'petunjuk', '_meta'}:
        tail = f'_{suffix}'
        title = original[:31-len(tail)] + tail
        suffix += 1
    used.add(title.casefold())
    return title


def add_instructions(wb, unit, start, end):
    ws = wb.active
    ws.title = 'Petunjuk'
    lines = [('TEMPLATE PENGUKURAN BERAULOAD', ''),
             ('Unit', unit.name), ('Kode Unit', unit.code),
             ('Periode', f'{start} s.d. {end} (WITA)'),
             ('Pengisian', 'Masukkan hanya angka pada sel berwarna kuning mulai C4.'),
             ('Kosong', 'Sel kosong dilewati; isi 0 apabila pembacaan benar-benar nol.'),
             ('Jangan diubah', 'Baris 1–3 dan kolom Tanggal/Jam menjadi identitas template.'),
             ('Catatan', 'Nama kolom boleh diganti; kode baris 3 menentukan parameter.'),
             ('Contoh', 'Pada sel C4 isi 125.5 sebagai contoh, bukan nilai otomatis.'),
             ('Impor', 'Pratinjau terlebih dahulu; hari verified/final tidak diubah.')]
    for left, right in lines:
        ws.append([excel_text(left), excel_text(right)])
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 92
    ws['A1'].font = Font(bold=True, color='176C7E', size=15)


def add_data_sheet(wb, tab, metrics, start, end, used):
    ws = wb.create_sheet(safe_sheet_name(tab.name, used))
    ws.append(['Tanggal', 'Jam'] + [excel_text(m.name) for m in metrics])
    ws.append([DATE_FORMAT, '0-23'] + [excel_text(m.unit) for m in metrics])
    ws.append(['tanggal', 'jam'] + [m.code for m in metrics])
    days = (end-start).days+1
    for day_offset in range(days):
        day = start + timedelta(days=day_offset)
        for hour in range(24):
            ws.append([day.isoformat(), hour] + [None]*len(metrics))
    ws.freeze_panes = 'C4'
    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 9
    for index in range(3, len(metrics)+3):
        letter = get_column_letter(index)
        ws.column_dimensions[letter].width = 24
        for row in ws.iter_rows(min_row=4, max_row=ws.max_row,
                                min_col=index, max_col=index):
            cell = row[0]
            cell.protection = Protection(locked=False)
            cell.fill = PatternFill('solid', fgColor='FFF7D6')
    for row in ws.iter_rows(min_row=1, max_row=3):
        for cell in row:
            cell.fill = PatternFill('solid', fgColor='174057')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(wrap_text=True)
    rule = DataValidation(type='decimal', operator='between',
                          formula1='-999999999', formula2='999999999',
                          allow_blank=True)
    rule.errorTitle = 'Nilai tidak valid'
    rule.error = 'Masukkan angka desimal atau biarkan sel kosong.'
    rule.showErrorMessage = True
    rule.errorStyle = 'stop'
    ws.add_data_validation(rule)
    rule.add(f'C4:{get_column_letter(len(metrics)+2)}{ws.max_row}')
    ws.protection.sheet = True
    ws.protection.selectUnlockedCells = False
    ws.protection.selectLockedCells = True


def build(db, unit_id, unit, start, end, tabs=None):
    selected = eligible_tabs(db, unit_id)
    if tabs:
        requested = set(tabs)
        available = {tab.code for tab, _ in selected}
        if requested - available:
            raise ValueError('Tab tidak aktif/tidak memiliki parameter: ' + ', '.join(sorted(requested-available)))
        selected = [(tab, metrics) for tab, metrics in selected if tab.code in requested]
    if not selected:
        raise ValueError('Tidak ada tab input aktif yang dapat diunduh')
    wb = Workbook()
    add_instructions(wb, unit, start, end)
    used = set()
    for tab, metrics in selected:
        add_data_sheet(wb, tab, metrics, start, end, used)
    ws = wb.create_sheet('_meta')
    for key, value in [('template_kind','berauload_hourly'),
                       ('template_version',TEMPLATE_VERSION), ('unit_code',unit.code),
                       ('period_start',start.isoformat()), ('period_end',end.isoformat()),
                       ('generated_at',datetime.now(timezone.utc).isoformat())]:
        ws.append([key, value])
    ws.sheet_state = 'hidden'
    tmp = tempfile.NamedTemporaryFile(prefix='berauload_template_', suffix='.xlsx',
                                      delete=False)
    try:
        wb.save(tmp)
    finally:
        tmp.close()
    return tmp.name
