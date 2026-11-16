"""Local-only performance sample, 62 dates, 1 ULP and 5 KP, all hours populated."""
from datetime import date,datetime,timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from sqlalchemy import create_engine,event,insert,text
from sqlalchemy.orm import sessionmaker
from app.db import Base,HourRecord,Metric,Asset,Reading
from app.modules.org_units.models import OrgUnit
from app.modules.completeness.service import build
# Imports register ORM mappings (not production DB)
from app.main import app
with TemporaryDirectory(prefix='berau-stage6-bench-') as tmp:
    engine=create_engine('sqlite:///'+str(Path(tmp)/'test.db'))
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    start=date(2026,9,16)
    end=start+timedelta(days=61)
    with Session() as db:
        up3=OrgUnit(code='up3_bench',name='UP3 Bench',level='up3',active=True)
        db.add(up3);db.flush()
        ulp=OrgUnit(code='ulp_bench',name='ULP Bench',level='ulp',parent_id=up3.id,active=True)
        db.add(ulp);db.flush()
        kps=[OrgUnit(code=f'kp{i}',name=f'KP {i}',level='kp',parent_id=ulp.id,active=True) for i in range(5)]
        db.add_all(kps);db.flush()
        all_units=[ulp,*kps]
        for i,u in enumerate(all_units):
            asset=Asset(code=f'assetbench{i}',name='Asset Bench',kind='pembangkit',unit_id=u.id)
            db.add(asset);db.flush()
            db.add(Metric(code=f'loadbench{i}',name='Load Bench',unit='kW',group_name='REKAP',
                          input_mode='input',role_key='system.load',unit_id=u.id,asset_id=asset.id))
        db.flush()
        metrics=db.query(Metric).filter(Metric.code.like('loadbench%')).order_by(Metric.code).all()
        hours=[]
        for day_delta in range(62):
            d=start+timedelta(days=day_delta)
            for hour in range(24):
                hours.append({'day':d,'hour':hour,'timestamp_utc':datetime.combine(d,datetime.min.time())+timedelta(hours=hour-8)})
        db.execute(insert(HourRecord),hours)
        db.flush()
        slot_ids=[row[0] for row in db.query(HourRecord.id).order_by(HourRecord.id).all()]
        readings=[{'hour_id':h,'metric_id':m.id,'value':Decimal('0.0') if h%24==0 else Decimal('5.0'),
                   'source':'manual'} for h in slot_ids for m in metrics]
        db.execute(insert(Reading),readings);db.commit()
        layout=[(ulp,0)]+[(kp,1) for kp in kps]
        captured=[]
        def hook(_conn,_cursor,statement,parameters,context,executemany):
            if 'readings' in statement and 'GROUP BY' in statement.upper() and not captured:
                captured.append((statement,parameters))
        event.listen(engine,'before_cursor_execute',hook)
        times=[]
        for _ in range(6):
            t=perf_counter()
            data=build(db,layout,start,end,datetime(2026,11,17,0,0))
            times.append(perf_counter()-t)
        event.remove(engine,'before_cursor_execute',hook)
        assert len(data['rows'])==6 and all(row['summary']['filled_hours']==1488 for row in data['rows'])
        print('Rows in readings:',len(readings),'slots:',len(slot_ids),'cells:',len(data['rows'])*62)
        print('6 runs seconds:',[round(t,5) for t in times], 'median:',round(median(times),5))
        if captured:
            statement,parameters=captured[0]
            print('EXPLAIN QUERY PLAN:')
            for row in db.connection().exec_driver_sql('EXPLAIN QUERY PLAN '+statement,parameters).all():
                print(row)
    engine.dispose()
