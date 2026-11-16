"""Strict structural validation of a BerauLoad hourly workbook (no writes)."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from math import isfinite
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from .repository import eligible_tabs
from .workbook import TEMPLATE_VERSION

MAX_ERRORS = 200
MAX_UPLOAD = 15 * 1024 * 1024


class TemplateInvalid(ValueError):
    def __init__(self, errors):
        super().__init__('File template tidak valid')
        self.errors = errors[:MAX_ERRORS]


def issue(errors, sheet, cell, message):
    if len(errors) < MAX_ERRORS:
        errors.append({'sheet': sheet, 'cell': cell, 'message': message})


def parse_day(value):
    if isinstance(value, datetime):
        if value.time().hour or value.time().minute or value.time().second:
            raise ValueError('Tanggal tidak boleh memiliki jam')
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('Tanggal harus YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Tanggal harus YYYY-MM-DD')
    return parsed


def parse_number(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError('Sel harus angka desimal atau kosong')
    if isinstance(value, float) and not isfinite(value):
        raise ValueError('NaN/tak hingga tidak valid')
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Angka tidak valid') from exc
    if not number.is_finite():
        raise ValueError('NaN/tak hingga tidak valid')
    if number <= Decimal('-1e9') or number >= Decimal('1e9'):
        raise ValueError('Angka di luar batas input sistem')
    return number


def metadata(book, unit, errors):
    if '_meta' not in book.sheetnames:
        issue(errors, '_meta', 'A1', 'Sheet metadata _meta wajib ada')
        return None
    sheet = book['_meta']
    fields = {}
    for row in sheet.iter_rows(min_row=1, max_row=30, max_col=2, values_only=True):
        if row[0] is not None:
            if row[0] in fields:
                issue(errors, '_meta', 'A1', 'Kunci metadata ganda')
            fields[row[0]] = row[1]
    expected = {'template_kind': 'berauload_hourly',
                'template_version': TEMPLATE_VERSION, 'unit_code': unit.code}
    for key, value in expected.items():
        if fields.get(key) != value:
            issue(errors, '_meta', 'B1', f'{key} tidak sesuai dengan template/unit tujuan')
    try:
        start = parse_day(fields['period_start'])
        end = parse_day(fields['period_end'])
        if start > end or (end-start).days >= 92:
            raise ValueError('Rentang harus 1–92 hari')
    except (KeyError, TypeError, ValueError):
        issue(errors, '_meta', 'B4', 'Periode metadata tidak valid (maks. 92 hari)')
        return None
    try:
        datetime.fromisoformat(str(fields['generated_at']))
    except (KeyError, TypeError, ValueError):
        issue(errors, '_meta', 'B6', 'generated_at tidak valid')
    return start, end


def columns(sheet, allowed, claimed, errors):
    matched = {}
    limit = min(sheet.max_column or 0, 2000)
    if (sheet.max_column or 0) > 2000:
        issue(errors, sheet.title, 'C3', 'Terlalu banyak kolom')
    for col in range(3, limit+1):
        code = sheet.cell(3, col).value
        addr = f'{get_column_letter(col)}3'
        if code is None:
            issue(errors, sheet.title, addr, 'Kode parameter wajib ada')
        elif not isinstance(code, str) or code not in allowed:
            issue(errors, sheet.title, addr, f'Kode parameter tidak dikenal/nonaktif/bukan input: {str(code)[:60]}')
        elif code in claimed:
            issue(errors, sheet.title, addr, 'Kode parameter ganda antar-sheet')
        else:
            matched[col] = code
            claimed.add(code)
    if not matched:
        issue(errors, sheet.title, 'C3', 'Sheet tidak memiliki parameter input yang sah')
    return matched


def sheet_rows(sheet, mapping, start, end, errors, result):
    seen = set()
    max_rows = 3 + 92*24
    if (sheet.max_row or 0) > max_rows:
        issue(errors, sheet.title, 'A'+str(max_rows+1), 'Terlalu banyak baris')
    bound = min(sheet.max_row or 0, max_rows)
    max_col = max([2, *mapping])
    values_iter = sheet.iter_rows(min_row=4, max_row=bound,
                                  max_col=max_col, values_only=True)
    for line, cells in enumerate(values_iter, 4):
        if all(v is None for v in cells):
            continue
        try:
            day = parse_day(cells[0])
            if not start <= day <= end:
                raise ValueError('Tanggal di luar periode template')
        except (ValueError, TypeError) as exc:
            issue(errors, sheet.title, f'A{line}', str(exc))
            continue
        hour = cells[1]
        if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
            issue(errors, sheet.title, f'B{line}', 'Jam harus bilangan bulat 0–23')
            continue
        key = (day, hour)
        if key in seen:
            issue(errors, sheet.title, f'B{line}', 'Tanggal/jam ganda dalam sheet')
            continue
        seen.add(key)
        for col, code in mapping.items():
            addr = f'{get_column_letter(col)}{line}'
            try:
                value = parse_number(cells[col-1])
                if value is not None:
                    result[key][code] = value
            except (ValueError, IndexError) as exc:
                issue(errors, sheet.title, addr, str(exc))


def reject_formulas(workbook, errors):
    """Reject Excel formulas anywhere, including headers and instruction sheets."""
    for sheet in workbook:
        if (sheet.max_row or 0) > 2300 or (sheet.max_column or 0) > 2000:
            issue(errors, sheet.title, 'A1', 'Sheet terlalu besar')
            continue
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == 'f':
                    issue(errors, sheet.title, cell.coordinate,
                          'Formula Excel tidak boleh ada di template')
                if len(errors) >= MAX_ERRORS:
                    return


def parse(contents: bytes, db, unit_id: int, unit):
    if len(contents) > MAX_UPLOAD:
        raise TemplateInvalid([{'sheet': 'File', 'cell': 'A1', 'message': 'Ukuran maksimum 15 MB'}])
    errors = []
    try:
        with ZipFile(BytesIO(contents)) as zipped:
            if (len(zipped.infolist()) > 300 or
                sum(z.file_size for z in zipped.infolist()) > 120*1024*1024 or
                any('vbaProject.bin' in z.filename or 'externalLinks/' in z.filename
                    for z in zipped.infolist())):
                raise TemplateInvalid([{'sheet': 'File', 'cell': 'A1',
                    'message': 'Isi Excel terlalu besar atau berisi komponen eksternal/makro'}])
    except BadZipFile as exc:
        raise TemplateInvalid([{'sheet':'File','cell':'A1',
                                 'message':'File .xlsx rusak'}]) from exc
    try:
        book = load_workbook(BytesIO(contents), read_only=True,
                             data_only=True, keep_links=False)
        formulas = load_workbook(BytesIO(contents), read_only=True,
                                 data_only=False, keep_links=False)
    except Exception as exc:
        raise TemplateInvalid([{'sheet': 'File', 'cell': 'A1',
                                'message': 'File .xlsx tidak dapat dibuka'}]) from exc
    try:
        reject_formulas(formulas, errors)
        period = metadata(book, unit, errors)
        start, end = period if period else (date.min, date.min)
        permitted = {m.code: m for _, metrics in eligible_tabs(db, unit_id) for m in metrics}
        claimed = set()
        rows = defaultdict(dict)
        data_sheets = [s for s in book if s.title not in ('Petunjuk', '_meta')]
        if not data_sheets:
            issue(errors, 'File', 'A1', 'Tidak ada sheet data')
        if len(data_sheets) > 30:
            issue(errors, 'File', 'A1', 'Terlalu banyak sheet data')
        for sheet in data_sheets[:30]:
            mapping = columns(sheet, permitted, claimed, errors)
            if mapping and period:
                sheet_rows(sheet, mapping, start, end, errors, rows)
        if errors:
            raise TemplateInvalid(errors)
        return {'start': start, 'end': end, 'rows': dict(rows),
                'parameter_codes': sorted(claimed), 'unit_id': unit_id}
    finally:
        book.close()
        formulas.close()
