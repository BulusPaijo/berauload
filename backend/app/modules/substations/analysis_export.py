"""Safe bounded CSV/XLSX exports with definition-version provenance."""
import csv
import io
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from fastapi.responses import Response
from openpyxl import Workbook
from .models_calc import (GarduCalcColumn, GarduCalcRule, GarduCalcSettings)
from .models import SubstationField
from .analysis_data import decorate
from .common import dump

MAX_ROWS=10000
DEFAULT=['code','name','feeder','power_kva','measured_on',
         'session','state','reference','category','findings']
ATTRS={'code':'Gardu','name':'Nama gardu','feeder':'Penyulang',
       'power_kva':'Daya (kVA)','measured_on':'Tanggal ukur','session':'Sesi',
       'state':'Status verifikasi','status':'Status ukur','brand':'Merk',
       'address':'Alamat','reference':'Kolom acuan','category':'Kategori',
       'findings':'Temuan'}


def clean(value):
    if value is None:return ''
    if isinstance(value,(dict,list)):value=json.dumps(value,ensure_ascii=False)
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')):
        return "'"+value
    return value


def columns_for(db, codes):
    cols={c.code:c for c in db.query(GarduCalcColumn).filter_by(active=True)}
    extra={'extra_'+f.code:f.name for f in db.query(SubstationField).filter_by(active=True)}
    if codes:
        if any(c not in cols and c not in ATTRS and c not in extra for c in codes):
            raise HTTPException(422,'Kolom ekspor tidak dikenal atau diarsipkan')
        keys=list(dict.fromkeys(codes))
    else:keys=DEFAULT
    if not 1<=len(keys)<=100:raise HTTPException(422,'Maksimal 100 kolom ekspor')
    return keys,{key:(cols[key].name if key in cols else extra[key] if key in extra
                      else ATTRS[key]) for key in keys}


def field(row, code):
    if code=='category':return row['category']['name']
    if code=='findings':return ', '.join(v['name'] for v in row['findings'])
    if code in row:return row[code]
    if code.startswith('extra_'):return row['extra_values'].get(code[6:])
    calc=row['columns'].get(code)
    if not calc:return None
    return str(calc['value'])+' (tidak lengkap)' if calc['incomplete'] and calc['value'] is not None else calc['value']


def metadata(db, opt, keys):
    settings=db.get(GarduCalcSettings,1)
    cols={c.code:c for c in db.query(GarduCalcColumn).all()}
    info=[('Dibuat pada',datetime.now(ZoneInfo('Asia/Makassar')).isoformat()),
          ('Versi definisi',settings.version if settings else None),
          ('Filter',json.dumps(opt.model_dump(mode='json'),ensure_ascii=False)),
          ('Kolom',', '.join(keys))]
    for key in keys:
        if key in cols:info.append((f'Rumus {key}',cols[key].expression))
    for rule in db.query(GarduCalcRule).filter_by(active=True):
        info.append((f'Aturan {rule.kind} {rule.code}',rule.expression))
    return info


def render(db, opt, query, format, keys=None, selected=None, branding='BerauLoad'):
    keys,names=columns_for(db,keys)
    if selected is not None:
        if len(selected)>MAX_ROWS:raise HTTPException(422,'Terlalu banyak ID dipilih')
        # Only rows included in the active filter can be selected.
        from .models import Substation, SubstationMeasurement
        existing=[n for n in selected if n>0]
        without_visit=[-n for n in selected if n<0]
        query=query.filter((SubstationMeasurement.id.in_(existing)) |
                           ((Substation.id.in_(without_visit)) & (SubstationMeasurement.id.is_(None))))
    total=query.order_by(None).count()
    if total>MAX_ROWS:
        raise HTTPException(422,f'Ekspor dibatasi {MAX_ROWS} baris, filter lagi (ada {total})')
    from .analysis_queries import sorted_query
    ordered=sorted_query(db,query,opt)
    data=[]
    # At most MAX_ROWS, in chunks so joined dataset does not require large memory.
    for offset in range(0,total,200):
        for row in decorate(db,ordered.offset(offset).limit(200).all()):
            data.append([clean(field(row,key)) for key in keys])
    notes=metadata(db,opt,keys)
    if format=='csv':
        output=io.StringIO();writer=csv.writer(output)
        writer.writerow([clean(names[key]) for key in keys]);writer.writerows(data)
        writer.writerow([]);writer.writerow(['KETERANGAN','Nilai'])
        writer.writerows((clean(a),clean(b)) for a,b in notes)
        payload='\ufeff'+output.getvalue()
        media='text/csv; charset=utf-8'
    elif format=='xlsx':
        wb=Workbook();sheet=wb.active;sheet.title='Analisa Gardu'
        sheet.append([clean(names[key]) for key in keys])
        for values in data:sheet.append(values)
        info=wb.create_sheet('Keterangan')
        for item in notes:info.append([clean(item[0]),clean(item[1])])
        output=io.BytesIO();wb.save(output);payload=output.getvalue()
        media='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:raise HTTPException(422,'Format ekspor harus csv atau xlsx')
    slug=re.sub('[^a-zA-Z0-9_-]+','-',branding)[:30].strip('-') or 'BerauLoad'
    filename=f'{slug}_Analisa_Gardu_{datetime.now().strftime("%Y%m%d")}.{format}'
    return Response(payload,media_type=media,headers={
        'Content-Disposition':f'attachment; filename="{filename}"'})
