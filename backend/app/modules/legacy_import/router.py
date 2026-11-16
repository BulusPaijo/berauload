"""Legacy Excel route. Supported exclusively for the original ULP."""
import calendar, hashlib, json, os, uuid
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...db import ImportBatch, AuditLog, HourRecord, Reading, Metric, get_db
from ...importer import parse_load_excel, MAX_FILE_BYTES
from ..org_units.context import UnitContext, unit_context, require_action, audit_details
from ..org_units.repository import home_unit
from ..formulas.service import active_plan, calculate_custom
from ..performance.cache import clear_reading_cache
from ..records.entry import save_readings
from ..unit_references.recalculation import recalculate
from ..records.service import day_status
router=APIRouter(prefix='/api', tags=['Legacy Import'])
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','/data/uploads'))
STAGING_DIR=UPLOAD_DIR/'staging'

def _legacy(ctx):
    if not ctx.unit.legacy_home:
        raise HTTPException(422,'Laporan lama hanya dapat diimport ke ULP Tanjung Redeb')

def audit(db,u,action,target,detail):
    db.add(AuditLog(user_id=u.id,action=action,target=target,detail=detail))

@router.get('/imports')
def imports(ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    rows=db.query(ImportBatch).filter_by(unit_id=ctx.id).order_by(ImportBatch.created_at.desc()).limit(100).all()
    return [{'id':r.id,'filename':r.filename,'year':r.year,'month':r.month,
             'hours_created':r.hours_created,'hours_skipped':r.hours_skipped,
             'readings_created':r.readings_created,'warnings':r.warnings,
             'created_at':r.created_at.isoformat() if r.created_at else None} for r in rows]

@router.post('/imports/preview')
async def preview_import(file:UploadFile=File(...),year:int=Form(...),month:int=Form(...),
                         ctx:UnitContext=Depends(unit_context('write_data')),db:Session=Depends(get_db)):
    _legacy(ctx)
    require_action(ctx,'operator')
    if not file.filename.lower().endswith('.xlsx'):raise HTTPException(422,'Format harus .xlsx')
    content=await file.read(MAX_FILE_BYTES+1)
    if len(content)>MAX_FILE_BYTES:raise HTTPException(413,'Ukuran maksimum 15 MB')
    try:parsed=parse_load_excel(content,year,month)
    except ValueError as exc:raise HTTPException(422,str(exc))
    exists=db.query(ImportBatch.id).filter_by(unit_id=ctx.id,sha256=parsed['sha256'],year=year,month=month).first()
    already=[]
    for r in db.query(HourRecord.day,HourRecord.hour).join(Reading,Reading.hour_id==HourRecord.id).join(Metric,Metric.id==Reading.metric_id).filter(Metric.unit_id==ctx.id,HourRecord.day>=date(year,month,1),HourRecord.day<=date(year,month,calendar.monthrange(year,month)[1])).distinct().all():
        already.append((r.day.isoformat(),r.hour))
    occupied=set(already)
    conflicts=sum((row['date'],row['hour']) in occupied for row in parsed['hours'])
    token=str(uuid.uuid4())
    STAGING_DIR.mkdir(parents=True,exist_ok=True)
    (STAGING_DIR/(token+'.xlsx')).write_bytes(content)
    (STAGING_DIR/(token+'.json')).write_text(json.dumps({'year':year,'month':month,
         'filename':Path(file.filename).name[:250],'sha256':parsed['sha256'],'unit_id':ctx.id,'user_id':ctx.actor.id}),encoding='utf8')
    return {'token':token,'duplicate_file':bool(exists),'period':f'{year}-{month:02d}',
            'hours_found':len(parsed['hours']),'readings_found':parsed['reading_count'],
            'existing_hour_conflicts':conflicts,'warnings':parsed['warnings'][:80],
            'sample':parsed['hours'][:3]}

class CommitRequest(BaseModel):
    token:str=Field(pattern=r'^[a-f0-9-]{36}$')

@router.post('/imports/commit')
def commit_import(body:CommitRequest,ctx:UnitContext=Depends(unit_context('write_data')),db:Session=Depends(get_db)):
    _legacy(ctx)
    require_action(ctx,'operator')
    meta_path=STAGING_DIR/(body.token+'.json')
    src_path=STAGING_DIR/(body.token+'.xlsx')
    if not meta_path.exists() or not src_path.exists():raise HTTPException(404,'Token pratinjau tidak ditemukan/kedaluwarsa')
    meta=json.loads(meta_path.read_text(encoding='utf8'));raw=src_path.read_bytes()
    if meta.get('unit_id')!=ctx.id or meta.get('user_id')!=ctx.actor.id:
        raise HTTPException(403,'Token bukan milik pengguna/unit ini')
    if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise HTTPException(409,'File staging berubah')
    if db.query(ImportBatch.id).filter_by(unit_id=ctx.id,sha256=meta['sha256'],year=meta['year'],month=meta['month']).first():
        raise HTTPException(409,'File identik sudah pernah diimport')
    try:parsed=parse_load_excel(raw,meta['year'],meta['month'])
    except ValueError as exc:raise HTTPException(422,str(exc))
    imported=0;skipped=0;measurements=0
    batch_id=str(uuid.uuid4())
    formula_plan=active_plan(db)
    batch=ImportBatch(id=batch_id,filename=meta['filename'],sha256=meta['sha256'],
                      unit_id=ctx.id,
                      year=meta['year'],month=meta['month'],created_by=ctx.actor.id,warnings=parsed['warnings'][:80])
    db.add(batch)
    # Prevent unintentional overwrite: only entirely new hour slots are inserted.
    # Existing verified/final hours are never replaced; even drafts require a
    # deliberate audited manual correction.
    start=date(meta['year'],meta['month'],1)
    end=date(meta['year'],meta['month'],calendar.monthrange(meta['year'],meta['month'])[1])
    occupied={(r.day.isoformat(),r.hour) for r in db.query(HourRecord.day,HourRecord.hour).join(Reading,Reading.hour_id==HourRecord.id).join(Metric,Metric.id==Reading.metric_id).filter(Metric.unit_id==ctx.id,HourRecord.day>=start,HourRecord.day<=end).distinct().all()}
    try:
        for row in parsed['hours']:
            key=(row['date'],row['hour'])
            if key in occupied or day_status(db,date.fromisoformat(row['date']),ctx.id)!='draft':
                skipped+=1;continue
            custom,_=calculate_custom(db,row['values'],plan=formula_plan)
            augmented={**row['values'],**{k:v for k,v in custom.items() if v is not None}}
            saved_day = date.fromisoformat(row['date'])
            save_readings(db,saved_day,row['hour'],augmented,
                          'excel_import',ctx.id,ctx.actor.id,batch_id,overwrite=False)
            recalculate(db, saved_day, row['hour'], ctx.id, set(augmented))
            imported+=1;measurements+=len(augmented);occupied.add(key)
        batch.hours_created=imported;batch.hours_skipped=skipped;batch.readings_created=measurements
        audit(db,ctx.actor,'import_commit',batch_id,audit_details(ctx,'operator',file=meta['filename'],created_hours=imported,skipped=skipped))
        db.commit()
        clear_reading_cache()
    except Exception:
        db.rollback();raise
    archive=UPLOAD_DIR/(batch_id+'.xlsx')
    archive.write_bytes(raw)
    meta_path.unlink(missing_ok=True);src_path.unlink(missing_ok=True)
    return {'id':batch_id,'hours_created':imported,'hours_skipped':skipped,
            'readings_created':measurements,'warnings':parsed['warnings'][:80]}

@router.get('/imports/{id}/source')
def source_file(id:str,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    require_action(ctx,'verifier')
    row=db.get(ImportBatch,id)
    if not row or row.unit_id!=ctx.id:raise HTTPException(404,'Import tidak ditemukan')
    path=UPLOAD_DIR/(row.id+'.xlsx')
    if not path.exists():raise HTTPException(404,'Arsip sumber belum tersedia')
    return StreamingResponse(open(path,'rb'),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition':f'attachment; filename="berauload-source-{row.id}.xlsx"'})

