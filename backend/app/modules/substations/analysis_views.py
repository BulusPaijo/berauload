"""Saved user/shared views; JSON is display config only, never executable code."""
from fastapi import HTTPException
from .analysis_models import GarduAnalysisView
from .models_calc import GarduCalcColumn, GarduCalcRule
from .common import audit, dump

VALID_KEYS = {'mode','session','start','end','unit_id','feeder_id','min_kva',
              'max_kva','category','findings','finding_mode','state','text','status',
              'numeric_code','numeric_op','numeric_min','numeric_max',
              'sort','desc','columns','widths','order','page_size','chart'}


def validate_layout(layout):
    if not isinstance(layout,dict) or len(layout)>35:
        raise HTTPException(422, 'Tampilan harus berupa objek')
    if set(layout)-VALID_KEYS:
        raise HTTPException(422, 'Field tampilan tidak dikenal')
    if not all(isinstance(v,(str,int,float,bool,list,dict,type(None))) for v in layout.values()):
        raise HTTPException(422,'Isi tampilan tidak sah')
    for name in ('columns','order','findings'):
        if name in layout and (not isinstance(layout[name], list) or len(layout[name])>100
                              or any(not isinstance(v,str) or len(v)>80 for v in layout[name])):
            raise HTTPException(422, 'Kolom tampilan tidak sah')
    if 'widths' in layout and (not isinstance(layout['widths'],dict)
        or len(layout['widths'])>100 or any(not isinstance(k,str) or not isinstance(v,int)
        or not 50<=v<=800 for k,v in layout['widths'].items())):
        raise HTTPException(422,'Lebar kolom tidak sah')
    return layout


def visible_views(db, ctx):
    rows = db.query(GarduAnalysisView).filter(
        (GarduAnalysisView.shared.is_(True)) | (GarduAnalysisView.owner_id==ctx.actor.id)).order_by(
         GarduAnalysisView.shared.desc(),GarduAnalysisView.name).all()
    columns={r.code for r in db.query(GarduCalcColumn).filter_by(active=True)}
    rules={r.code for r in db.query(GarduCalcRule).filter_by(active=True)}
    result=[]
    for row in rows:
        missing=[x for x in row.layout.get('columns',[]) if x not in columns and not x.startswith('extra_')
                 and x not in ('code','name','address','feeder','brand','power_kva',
                     'measured_on','session','state','status','reference','category','findings')]
        missing.extend(x for x in row.layout.get('findings',[]) if x not in rules)
        missing.extend(x for x in (row.layout.get('numeric_code'),row.layout.get('sort'))
                       if x and x not in columns and x not in ('code','name','address',
                       'feeder','brand','power_kva','measured_on','session','state',
                       'status','reference','category','findings') and not x.startswith('extra_'))
        if row.layout.get('category') and row.layout['category'] not in rules:
            missing.append(row.layout['category'])
        result.append({**dump(row),'warnings':missing})
    return result


def save_view(db, ctx, body, view_id=None):
    row = db.get(GarduAnalysisView,view_id) if view_id else None
    if view_id and row is None: raise HTTPException(404,'Tampilan tidak ditemukan')
    if row and not (row.owner_id==ctx.actor.id or (row.shared and ctx.superadmin)):
        raise HTTPException(403,'Tidak dapat mengubah tampilan pengguna lain')
    if not row and body.get('shared') and not ctx.superadmin:
        raise HTTPException(403,'Hanya admin membuat tampilan bersama')
    if row and row.shared and not ctx.superadmin:
        raise HTTPException(403,'Tampilan bersama hanya dapat diubah admin')
    name=body.get('name',row.name if row else '')
    if not isinstance(name,str) or not 1<=len(name.strip())<=150:
        raise HTTPException(422,'Nama tampilan wajib 1–150 karakter')
    shared=body.get('shared',row.shared if row else False)
    if not isinstance(shared,bool): raise HTTPException(422,'Status bersama tidak valid')
    if shared and not ctx.superadmin: raise HTTPException(403,'Hanya admin membuat tampilan bersama')
    layout=validate_layout(body.get('layout',row.layout if row else {}))
    old=dump(row) if row else None
    if body.get('is_default') and shared:
        raise HTTPException(422,'Tampilan bawaan pribadi tidak boleh bersama')
    if body.get('is_default'):
        db.query(GarduAnalysisView).filter_by(owner_id=ctx.actor.id).update({'is_default':False})
    duplicate=db.query(GarduAnalysisView).filter_by(
        owner_id=None if shared else ctx.actor.id,name=name.strip()).first()
    if duplicate and (not row or duplicate.id!=row.id):
        raise HTTPException(409,'Nama tampilan sudah digunakan')
    if not row:
        row=GarduAnalysisView(owner_id=None if shared else ctx.actor.id)
        db.add(row)
    row.name,row.shared,row.layout=name.strip(),shared,layout
    row.owner_id=None if shared else ctx.actor.id
    if 'is_default' in body:row.is_default=bool(body['is_default'])
    db.flush()
    audit(db,ctx,'gardu_analysis_view_save',row.id,old,dump(row))
    return dump(row)
