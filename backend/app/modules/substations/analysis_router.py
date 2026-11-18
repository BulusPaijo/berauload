"""Stage 9c query, summary, export and user view endpoints (global definitions)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import get_db
from ..org_units.context import unit_context, UnitContext
from .analysis_models import GarduAnalysisSettings, GarduAnalysisView
from .analysis_queries import filtered, reference, rows
from .analysis_data import decorate, summary
from .analysis_export import render
from .analysis_views import visible_views, save_view
from .models_calc import GarduCalcColumn, GarduCalcSettings
from .models import SubstationMeasurement, SubstationValue
from .common import audit, child_ids, dump, require_admin

router=APIRouter(prefix='/api/substations/analysis',tags=['Gardu Analysis'])

class AnalysisOptions(BaseModel):
    mode:str='terakhir'
    start:date|None=None
    end:date|None=None
    session:str='tertinggi'
    unit_id:int|None=None
    feeder_id:int|None=None
    min_kva:float|None=None
    max_kva:float|None=None
    category:str=''
    findings:list[str]=[]
    finding_mode:str='any'
    state:str=''
    status:str=''
    text:str=''
    numeric_code:str=''
    numeric_op:str=''
    numeric_min:float|None=None
    numeric_max:float|None=None
    sort:str='code'
    desc:bool=False
    page:int=Field(default=1,ge=1)
    page_size:int=Field(default=50,ge=1,le=200)


def options_with_findings(opt:AnalysisOptions=Depends(),
                          findings:list[str]=Query(default=[])):
    """FastAPI only binds repeated list query parameters on a real dependency.

    Also accept comma-separated codes, including mixed/repeated forms.
    """
    opt.findings=[code.strip() for item in findings for code in item.split(',')
                  if code.strip()]
    return opt


def validate_options(db,opt):
    if opt.numeric_op not in ('','gte','lte','antara','kosong','ada'):
        raise HTTPException(422,'Operator syarat angka tidak dikenal')
    if opt.numeric_code:
        if not opt.numeric_op:
            raise HTTPException(422,'Pilih operator syarat angka')
        if opt.numeric_op in ('gte','lte','antara') and opt.numeric_min is None:
            raise HTTPException(422,'Nilai pembanding minimum wajib diisi')
        if opt.numeric_op=='antara' and opt.numeric_max is None:
            raise HTTPException(422,'Nilai pembanding maksimum wajib diisi')
        if (opt.numeric_op=='antara' and opt.numeric_max is not None
                and opt.numeric_min is not None and opt.numeric_min>opt.numeric_max):
            raise HTTPException(422,'Nilai minimum melebihi maksimum')
    elif opt.numeric_op or opt.numeric_min is not None or opt.numeric_max is not None:
        raise HTTPException(422,'Pilih kolom hitung untuk syarat angka')
    if opt.start and opt.end and opt.start>opt.end:
        raise HTTPException(422,'Tanggal mulai melebihi akhir')
    if opt.finding_mode not in ('any','all'):
        raise HTTPException(422,'Cara mencocokkan temuan harus any/all')
    if len(opt.findings)>40 or len(opt.text)>180:
        raise HTTPException(422,'Filter terlalu panjang')
    if opt.status not in ('','baru','lama','belum'):
        raise HTTPException(422,'Status ukur tidak dikenal')
    if opt.session!='tertinggi':
        from .models import SubstationSession
        if not db.query(SubstationSession.id).filter_by(code=opt.session,active=True).first():
            raise HTTPException(422,'Sesi tidak dikenal')
    if opt.findings:
        from .models_calc import GarduCalcRule
        valid={r.code for r in db.query(GarduCalcRule).filter_by(kind='finding',active=True)}
        if set(opt.findings)-valid:raise HTTPException(422,'Kode temuan tidak dikenal')
    if opt.category and opt.category!='tidak_dapat_dinilai':
        from .models_calc import GarduCalcRule
        if not db.query(GarduCalcRule.id).filter_by(
                code=opt.category,kind='category',active=True).first():
            raise HTTPException(422,'Kategori tidak dikenal')
    return opt


@router.get('/definitions')
def definitions(db:Session=Depends(get_db),ctx:UnitContext=Depends(unit_context('read'))):
    from .models_calc import GarduCalcRule
    from .models import SubstationSession, SubstationFeeder, SubstationField
    from ..org_units.models import OrgUnit
    ref=reference(db)
    return {'reference_code':ref.code if ref else None,
        'columns':[dump(r) for r in db.query(GarduCalcColumn).filter_by(active=True).order_by(
             GarduCalcColumn.display_order)],
        'rules':[dump(r) for r in db.query(GarduCalcRule).filter_by(active=True).order_by(
             GarduCalcRule.display_order)],
        'sessions':[dump(r) for r in db.query(SubstationSession).filter_by(active=True)],
        'feeders':[dump(r) for r in db.query(SubstationFeeder).filter(
             SubstationFeeder.unit_id.in_(child_ids(db,ctx)))],
        'fields':[dump(r) for r in db.query(SubstationField).filter_by(active=True)],
        'units':[dump(r,('id','name','level','parent_id')) for r in db.query(OrgUnit).filter(
            OrgUnit.id.in_(child_ids(db,ctx))).order_by(OrgUnit.level,OrgUnit.name)]}


@router.post('/settings')
def update_reference(body:dict,db:Session=Depends(get_db),
                     ctx:UnitContext=Depends(unit_context('read'))):
    require_admin(ctx)
    column=db.query(GarduCalcColumn).filter_by(code=body.get('reference_code'),active=True).first()
    if not column:raise HTTPException(422,'Kolom acuan harus kolom hitung aktif')
    settings=db.get(GarduAnalysisSettings,1)
    before=dump(settings) if settings else None
    if not settings:settings=GarduAnalysisSettings(id=1);db.add(settings)
    settings.reference_column_id=column.id
    db.flush();audit(db,ctx,'gardu_analysis_reference',1,before,dump(settings));db.commit()
    return {'reference_code':column.code}


@router.get('/rows')
def list_rows(opt:AnalysisOptions=Depends(options_with_findings),db:Session=Depends(get_db),
              ctx:UnitContext=Depends(unit_context('read'))):
    validate_options(db,opt)
    query=filtered(db,ctx,opt)
    total,chosen=rows(db,query,opt,opt.page_size)
    data=decorate(db,chosen)
    return {'total':total,'page':opt.page,'page_size':opt.page_size,
            'items':data,'reference_code':reference(db).code if reference(db) else None,
            'version':db.get(GarduCalcSettings,1).version}


@router.get('/summary')
def get_summary(opt:AnalysisOptions=Depends(options_with_findings),db:Session=Depends(get_db),
                ctx:UnitContext=Depends(unit_context('read'))):
    validate_options(db,opt)
    return summary(db,filtered(db,ctx,opt))


@router.get('/export')
def export_file(format:str='xlsx', columns:str='', ids:str='',
                opt:AnalysisOptions=Depends(options_with_findings),db:Session=Depends(get_db),
                ctx:UnitContext=Depends(unit_context('read'))):
    validate_options(db,opt)
    selected=None
    if ids:
        try: selected=[int(x) for x in ids.split(',')]
        except ValueError: raise HTTPException(422,'Daftar ID tidak sah')
        if len(selected)>10000:raise HTTPException(422,'Terlalu banyak ID')
    from ..branding.models import AppBranding
    brand=db.get(AppBranding,1)
    return render(db,opt,filtered(db,ctx,opt),format,
                  [x for x in columns.split(',') if x] or None,
                  selected,brand.app_short_name if brand and brand.app_short_name else 'BerauLoad')


@router.get('/measurements/{id}')
def detail(id:int,db:Session=Depends(get_db),
           ctx:UnitContext=Depends(unit_context('read'))):
    m=db.get(SubstationMeasurement,id)
    if not m or m.unit_id not in child_ids(db,ctx):
        raise HTTPException(404,'Pengukuran tidak ditemukan')
    from .calculation_service import get_results
    history=db.query(SubstationMeasurement).filter_by(substation_id=m.substation_id).order_by(
        SubstationMeasurement.measured_on.desc(),SubstationMeasurement.id.desc()).limit(40).all()
    values=db.query(SubstationValue).filter_by(measurement_id=id).all()
    return {'measurement':dump(m),'values':[dump(v) for v in values],
            'calculated':get_results(db,id),
            'history':[dump(r,('id','measured_on','session','state','revision')) for r in history]}


@router.get('/views')
def get_views(db:Session=Depends(get_db),ctx:UnitContext=Depends(unit_context('read'))):
    return visible_views(db,ctx)


@router.post('/views')
def create_view(body:dict,db:Session=Depends(get_db),
                ctx:UnitContext=Depends(unit_context('read'))):
    result=save_view(db,ctx,body);db.commit();return result


@router.patch('/views/{id}')
def edit_view(id:int,body:dict,db:Session=Depends(get_db),
                ctx:UnitContext=Depends(unit_context('read'))):
    result=save_view(db,ctx,body,id);db.commit();return result


@router.delete('/views/{id}')
def delete_view(id:int,db:Session=Depends(get_db),
                ctx:UnitContext=Depends(unit_context('read'))):
    row=db.get(GarduAnalysisView,id)
    if not row:raise HTTPException(404,'Tampilan tidak ditemukan')
    if not ((row.owner_id==ctx.actor.id) or (row.shared and ctx.superadmin)):
        raise HTTPException(403,'Tidak dapat menghapus tampilan lain')
    audit(db,ctx,'gardu_analysis_view_delete',row.id,dump(row),None)
    db.delete(row);db.commit();return {'deleted':True}


@router.get('/charts')
def get_charts(station_id:int|None=None,
               opt:AnalysisOptions=Depends(options_with_findings),
               db:Session=Depends(get_db),
               ctx:UnitContext=Depends(unit_context('read'))):
    validate_options(db,opt)
    from .analysis_charts import charts
    return charts(db,ctx,opt,station_id)


@router.get('/stations/{id}/latest')
def latest_for_station(id:int,db:Session=Depends(get_db),
                       ctx:UnitContext=Depends(unit_context('read'))):
    from .models import Substation
    station=db.get(Substation,id)
    if not station or station.unit_id not in child_ids(db,ctx):
        raise HTTPException(404,'Gardu tidak ditemukan')
    row=db.query(SubstationMeasurement.id).filter_by(substation_id=id).order_by(
        SubstationMeasurement.measured_on.desc(),SubstationMeasurement.id.desc()).first()
    return {'measurement_id':row.id if row else None}


@router.get('/stations/{id}/trend')
def station_trend(id:int,days:int=Query(365,ge=7,le=3660),db:Session=Depends(get_db),
                  ctx:UnitContext=Depends(unit_context('read'))):
    """9d-3: light per-gardu history of the reference column per session (no full chart scan)."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from .models import Substation
    from .models_calc import GarduCalcValue
    station=db.get(Substation,id)
    if not station or station.unit_id not in child_ids(db,ctx):
        raise HTTPException(404,'Gardu tidak ditemukan')
    ref=reference(db)
    if not ref:return {'reference_code':None,'trend':[]}
    m=SubstationMeasurement
    cutoff=datetime.now(ZoneInfo('Asia/Makassar')).date()-timedelta(days=days)
    rows=db.query(m.measured_on,m.session,GarduCalcValue.value).join(GarduCalcValue,
        (GarduCalcValue.measurement_id==m.id)&(GarduCalcValue.column_id==ref.id)).filter(
        m.substation_id==id,m.measured_on>=cutoff).order_by(m.measured_on,m.session).limit(400).all()
    return {'reference_code':ref.code,'unit':ref.unit,'trend':[{'day':d.isoformat(),'session':s,'value':v}
            for d,s,v in rows if v is not None]}
