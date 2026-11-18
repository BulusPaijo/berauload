"""Single-measurement Excel download (9d-5): same layout as the 'Tabel nilai' tab."""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from .analysis_export import clean
from .models import SubstationParam

ARIAL = 'Arial'
HEAD = PatternFill('solid', fgColor='E8EEF5')
CHANGED = PatternFill('solid', fgColor='FCD9B6')
THIN = Side(style='thin', color='C8CED6')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _font(bold=False, color='1F2937', size=10):
    return Font(name=ARIAL, bold=bold, color=color, size=size)


def _text(value):
    return None if value is None else clean(value)


def _put(ws, row, col, value, bold=False, fill=None, fmt=None, align=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = _font(bold)
    cell.border = BOX
    if fill:
        cell.fill = fill
    if fmt:
        cell.number_format = fmt
    if align:
        cell.alignment = Alignment(horizontal=align, vertical='center')
    return cell


def _unit(u):
    return 'Ω' if str(u or '').lower() == 'ohm' else u


def _shown(value, flag):
    return flag if flag else value


def build(db, visit, head, calculated, changed):
    params = db.query(SubstationParam).filter_by(active=True).order_by(
        SubstationParam.display_order, SubstationParam.id).all()
    values = {(v['param_id'], v['line_no']): v for v in visit['values']}
    old = {(c['param_id'], c['line_no']): c for c in changed}
    wb = Workbook()
    ws = wb.active
    ws.title = 'Pengukuran'
    ws['A1'] = f"Pengukuran gardu {head.get('substation_code') or ''}"
    ws['A1'].font = _font(True, size=13)
    info = [('Kode gardu', head.get('substation_code')), ('Nama gardu', head.get('substation_name')),
            ('Unit', head.get('unit_name')), ('Penyulang', head.get('feeder_name')),
            ('Daya (kVA)', visit.get('snapshot_power_kva')),
            ('Jumlah jurusan', visit.get('snapshot_line_count')),
            ('Tanggal', visit.get('measured_on')), ('Sesi', head.get('session_name')),
            ('Jam ukur', visit.get('measured_at')), ('Petugas', visit.get('technician')),
            ('Status', 'Terverifikasi' if visit.get('state') == 'verified' else 'Draft'), ('Revisi', visit.get('revision')),
            ('Terakhir diubah oleh', head.get('updated_by_name'))]
    for i, (label, value) in enumerate(info, start=3):
        _put(ws, i, 1, label, bold=True, fill=HEAD)
        _put(ws, i, 2, _text(value) if isinstance(value, str) else value)
    row = len(info) + 4
    line_params = [p for p in params if p.scope == 'line']
    gardu_params = [p for p in params if p.scope == 'substation']
    ws.cell(row=row, column=1, value='Nilai per jurusan').font = _font(True, size=11)
    row += 1
    _put(ws, row, 1, 'Jurusan', bold=True, fill=HEAD, align='center')
    for c, p in enumerate(line_params, start=2):
        _put(ws, row, c, f'{p.name} ({_unit(p.unit)})', bold=True, fill=HEAD, align='center')
    labels = head.get('line_labels') or []
    for line in range(1, int(visit.get('snapshot_line_count') or 1) + 1):
        row += 1
        label = labels[line - 1] if line - 1 < len(labels) and labels[line - 1] else f'Jurusan {line}'
        _put(ws, row, 1, _text(label), bold=True)
        for c, p in enumerate(line_params, start=2):
            _cell(ws, row, c, values.get((p.id, line)), old.get((p.id, line)))
    row += 2
    ws.cell(row=row, column=1, value='Nilai gardu (sekali per gardu)').font = _font(True, size=11)
    row += 1
    for c, label in enumerate(('Parameter', 'Nilai', 'Satuan'), start=1):
        _put(ws, row, c, label, bold=True, fill=HEAD)
    for p in gardu_params:
        row += 1
        _put(ws, row, 1, p.name)
        _cell(ws, row, 2, values.get((p.id, 0)), old.get((p.id, 0)))
        _put(ws, row, 3, _unit(p.unit))
    columns = (calculated or {}).get('columns') or []
    if columns:
        row += 2
        ws.cell(row=row, column=1, value='Hasil hitung').font = _font(True, size=11)
        row += 1
        for c, label in enumerate(('Kolom', 'Nilai', 'Satuan'), start=1):
            _put(ws, row, c, label, bold=True, fill=HEAD)
        for col in columns:
            row += 1
            _put(ws, row, 1, col['name'])
            dec = int(col.get('decimals') or 0)
            _put(ws, row, 2, col.get('value'), fmt='0' if dec == 0 else '0.' + '0' * dec)
            _put(ws, row, 3, col.get('unit') or '')
    findings = (calculated or {}).get('matches') or []
    if findings:
        row += 2
        ws.cell(row=row, column=1, value='Kategori & temuan').font = _font(True, size=11)
        for f in findings:
            row += 1
            _put(ws, row, 1, 'Kategori' if f['kind'] == 'category' else 'Temuan', bold=True)
            _put(ws, row, 2, f['name'])
    if changed:
        row += 2
        note = ws.cell(row=row, column=1, value='Sel oranye = berubah pada revisi terakhir; '
                                                'nilai lama ada di komentar sel.')
        note.font = _font(color='9A5B13', size=9)
    ws.column_dimensions['A'].width = 24
    for c in range(2, max(len(line_params), 3) + 2):
        ws.column_dimensions[get_column_letter(c)].width = 16
    ws.freeze_panes = None
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def _cell(ws, row, col, value, old):
    shown = _shown(value.get('value') if value else None, value.get('flag') if value else None)
    cell = _put(ws, row, col, _text(shown) if isinstance(shown, str) else shown, align='right')
    if old is not None:
        cell.fill = CHANGED
        before = _shown(old.get('before'), old.get('before_flag'))
        cell.comment = Comment(f'Sebelumnya: {"kosong" if before is None else before}', 'BerauLoad')
    return cell
