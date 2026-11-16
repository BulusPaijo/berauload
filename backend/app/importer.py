from __future__ import annotations
import calendar
import hashlib
import io
from datetime import date, datetime
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from openpyxl.utils.datetime import from_excel
from .catalog import UPPER, LOWER

MAX_FILE_BYTES = 15 * 1024 * 1024

def is_number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool)

def parse_load_excel(raw:bytes, year:int, month:int):
    """Parse only real daily sheets, using cached formula results as source snapshots.

    Input period is explicit, so copied legacy workbook names/headers cannot silently
    turn a November sheet #31 into a fabricated December measurement.
    """
    if not 2020 <= year <= 2100 or not 1 <= month <= 12:
        raise ValueError('Periode tidak valid')
    if not raw or len(raw)>MAX_FILE_BYTES:
        raise ValueError('File kosong atau melebihi 15 MB')
    try:
        wb=load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:
        raise ValueError('File Excel tidak valid / tidak dapat dibaca') from exc
    maxday=calendar.monthrange(year,month)[1]
    warnings=[]
    data=[]
    found=0
    for day in range(1,maxday+1):
        ws=wb[str(day)] if str(day) in wb.sheetnames else None
        if ws is None:
            warnings.append(f'Sheet hari {day} tidak ditemukan')
            continue
        found+=1
        # The legacy file stores an Excel serial date at B2, possibly wrongly
        # copied; warn, but ALWAYS use the explicitly selected import period.
        cells=list(ws.iter_rows(min_row=1,max_row=59,min_col=1,max_col=32,values_only=True))
        def cell(col, row):
            index=column_index_from_string(col)-1
            return cells[row-1][index] if row <= len(cells) and index < len(cells[row-1]) else None
        ref=cell('B',2)
        if is_number(ref):
            try: ref=from_excel(ref)
            except Exception: ref=None
        if isinstance(ref, datetime): ref=ref.date()
        if isinstance(ref,date) and ref!=date(year,month,day):
            warnings.append(f'Sheet {day}: tanggal B2 berbeda ({ref.isoformat()})')
        for hour in range(24):
            top=hour+9; bottom=hour+36
            values={}
            # Detect real source observations. Calculated cells and blank template
            # formula outputs MUST NOT create fake readings.
            primary_count=0
            for col, code in UPPER.items():
                val=cell(col,top)
                if is_number(val):
                    values[code]=float(val)
                    if col not in ('O',): primary_count+=1
            for col,code in LOWER.items():
                val=cell(col,bottom)
                if is_number(val): values[code]=float(val)
            manual_lower=('incoming_gi_kw','tambang_lapor_kw','pltd_berau_kw','beban_suaran_kw','beban_padam_kw')
            # Some daily sheets have only recap entries; include if explicitly nonzero.
            lower_actual=any(values.get(k) not in (None,0) for k in manual_lower)
            if primary_count==0 and not lower_actual:
                continue
            # Empty cached formulas sometimes return 0, but these are not real
            # measurements. Do not copy derived zeros in otherwise blank fields.
            if values.get('beban_sistem_kw')==0 and 'jumlah_beban_kw' not in values:
                values.pop('beban_sistem_kw',None)
            data.append({'date': date(year,month,day).isoformat(), 'hour':hour,
                         'values':values})
    wb.close()
    if not found:
        raise ValueError('Tidak ada sheet harian bernama 1, 2, 3, ... pada periode ini')
    # sheet 31 should never be imported for 30-day months
    if str(maxday+1) in wb.sheetnames and maxday<31:
        warnings.append(f'Sheet {maxday+1} diabaikan karena bukan tanggal dalam bulan {month}')
    return {'year':year,'month':month,'hours':data,'warnings':warnings,
            'days_present':found,'reading_count':sum(len(h['values']) for h in data),
            'sha256':hashlib.sha256(raw).hexdigest()}
