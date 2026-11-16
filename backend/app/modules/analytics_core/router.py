"""Stage 3 modular route extraction; legacy URL and behavior preserved."""
import calendar
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ...db import Metric, Reading, HourRecord, User, get_db
from ..org_units.models import UnitDayState
from ..org_units.context import UnitContext, unit_context, require_metric
from ...security import current_user
from ..standard_reports.service import compare_years
from ..org_units.repository import home_unit as org_home
from ..org_units.roles import metric_for_role, SYSTEM_LOAD
TZ = ZoneInfo('Asia/Makassar')
router = APIRouter(prefix='/api', tags=['Analytics'])

def load_analytics(db,metric,granularity,start,end,unit_id):
    m=require_metric(db,metric,unit_id)
    if granularity=='hour': group=[HourRecord.day,HourRecord.hour]
    elif granularity=='day':group=[HourRecord.day]
    elif granularity=='month':group=[func.extract('year',HourRecord.day),func.extract('month',HourRecord.day)]
    else:group=[func.extract('year',HourRecord.day)]
    rows=(db.query(*group,func.min(Reading.value),func.max(Reading.value),func.avg(Reading.value),func.count(Reading.id))
          .join(Reading,Reading.hour_id==HourRecord.id)
          .filter(HourRecord.day>=start,HourRecord.day<=end,Reading.metric_id==m.id)
          .group_by(*group).order_by(*group).all())
    data=[]
    for row in rows:
        n=len(group);key=row[:n]
        if granularity=='hour':label=f'{key[0]} {int(key[1]):02d}:00'
        elif granularity=='day':label=str(key[0])
        elif granularity=='month':label=f'{int(key[0])}-{int(key[1]):02d}'
        else:label=str(int(key[0]))
        low,peak,mean,cnt=row[n:]
        data.append({'period':label,'min':float(low),'peak':float(peak),'avg':round(float(mean),3),'count':cnt})
    return {'metric':metric,'unit':m.unit,'granularity':granularity,
            'start':str(start),'end':str(end),'data':data}

@router.get('/analytics')
def analytics(metric:str|None=None,granularity:str='day',start:date|None=None,end:date|None=None,
              ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    if not start:start=datetime.now(TZ).date().replace(day=1)
    if not end:end=datetime.now(TZ).date()
    if end<start or (end-start).days>365*35:raise HTTPException(422,'Rentang maksimal 35 tahun')
    if granularity not in ('hour','day','month','year'):raise HTTPException(422,'Granularitas tidak dikenal')
    if granularity=='hour' and (end-start).days>31:raise HTTPException(422,'Grafik per jam maksimal 31 hari')
    if granularity=='day' and (end-start).days>366:raise HTTPException(422,'Grafik harian maksimal 366 hari')
    if metric is None:
        main=metric_for_role(db,ctx.id,SYSTEM_LOAD)
        if main is None:return {'configured':False,'metric':None,'unit':None,'granularity':granularity,'start':str(start),'end':str(end),'data':[]}
        metric=main.code
    return load_analytics(db,metric,granularity,start,end,ctx.id)

@router.get('/dashboard')
def dashboard(year:int,month:int,ctx:UnitContext=Depends(unit_context('read')),db:Session=Depends(get_db)):
    if not 2020<=year<=2100 or not 1<=month<=12:raise HTTPException(422,'Periode tidak valid')
    start=date(year,month,1);end=date(year,month,calendar.monthrange(year,month)[1])
    m=metric_for_role(db,ctx.id,SYSTEM_LOAD)
    if m is None:
        return {'configured':False,'year':year,'month':month,'peak_kw':None,'peak_at':None,
                'min_kw':None,'avg_kw':None,'readings_count':None,'expected_hours_to_date':None,
                'coverage_pct':None,'final_days':None,'daily':[]}
    rows=(db.query(HourRecord.day,HourRecord.hour,Reading.value)
          .join(Reading,Reading.hour_id==HourRecord.id)
          .filter(HourRecord.day>=start,HourRecord.day<=end,Reading.metric_id==m.id)
          .order_by(HourRecord.day,HourRecord.hour).all())
    vals=[float(v) for _,_,v in rows]
    byday=defaultdict(list)
    for d,h,v in rows:byday[str(d)].append(float(v))
    end_effective=min(end,datetime.now(TZ).date())
    expected=max(0,(end_effective-start).days+1)*24
    states=db.query(UnitDayState).filter(UnitDayState.unit_id==ctx.id,UnitDayState.day>=start,UnitDayState.day<=end).all()
    peak=max(rows,key=lambda x:float(x[2])) if rows else None
    return {'year':year,'month':month,'peak_kw':max(vals) if vals else None,
            'peak_at':f'{peak[0]} {peak[1]:02d}:00' if peak else None,
            'min_kw':min(vals) if vals else None,'avg_kw':round(sum(vals)/len(vals),3) if vals else None,
            'readings_count':len(vals),'expected_hours_to_date':expected,
            'coverage_pct':round(len(vals)/expected*100,2) if expected else None,
            'final_days':sum(s.status=='final' for s in states),
            'daily':[{'date':d,'peak_kw':max(v),'avg_kw':round(sum(v)/len(v),3),'count':len(v)} for d,v in sorted(byday.items())]}

@router.get('/compare')
def compare(year_a:int, year_b:int, metric:str|None=None,
            aggregate:str='max', ctx:UnitContext=Depends(unit_context('read')),
            db:Session=Depends(get_db)):
    """Compatibility endpoint: legacy peak fields retained; aggregate is optional."""
    if metric is None:
        main=metric_for_role(db,ctx.id,SYSTEM_LOAD)
        if main is None:return {'configured':False,'year_a':year_a,'year_b':year_b,
                                'metric':None,'metric_name':None,'unit':None,
                                'aggregation':aggregate,'data':[]}
        metric=main.code
    require_metric(db,metric,ctx.id)
    return compare_years(db, year_a, year_b, metric, aggregate)

