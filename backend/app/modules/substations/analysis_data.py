"""Batch rendering and complete-filter SQL aggregates for stage 9c."""
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from sqlalchemy import func
from .models import Substation, SubstationFeeder, SubstationMeasurement, SubstationValue
from .models_calc import (GarduCalcColumn, GarduCalcMatch, GarduCalcMark,
                          GarduCalcRule, GarduCalcValue, GarduCalcSettings)
from .common import dump
from .analysis_queries import reference


def decorate(db, selected):
    ids = [r.mid for r in selected if r.mid]
    stations = {s.id:s for s in db.query(Substation).filter(
        Substation.id.in_([r.sid for r in selected])).all()}
    visits = {m.id:m for m in db.query(SubstationMeasurement).filter(
        SubstationMeasurement.id.in_(ids)).all()}
    feeders = {f.id:f for f in db.query(SubstationFeeder).filter(
        SubstationFeeder.id.in_([s.feeder_id for s in stations.values() if s.feeder_id])).all()}
    columns = {c.id:c for c in db.query(GarduCalcColumn).filter_by(active=True)}
    rules = {r.id:r for r in db.query(GarduCalcRule).filter_by(active=True)}
    cell_map = defaultdict(dict)
    for item in db.query(GarduCalcValue).filter(GarduCalcValue.measurement_id.in_(ids)):
        col = columns.get(item.column_id)
        if col:
            cell_map[item.measurement_id][col.code] = {'value': item.value,
                'incomplete':item.incomplete, 'note':item.note, 'version':item.version}
    matches = defaultdict(list)
    for item in db.query(GarduCalcMatch).filter(GarduCalcMatch.measurement_id.in_(ids)):
        rule = rules.get(item.rule_id)
        if rule: matches[item.measurement_id].append({'code':rule.code,
            'name':rule.name,'kind':rule.kind,'group_name':rule.group_name,
            'color':rule.color,'marker':rule.marker})
    marks = {r.measurement_id:r.version for r in db.query(GarduCalcMark).filter(
        GarduCalcMark.measurement_id.in_(ids))}
    ref = reference(db)
    sessions = _session_values(db, [r.sid for r in selected], ref)
    settings = db.get(GarduCalcSettings,1)
    version = settings.version if settings else 0
    follow = _followups(db, [r.sid for r in selected])
    today = datetime.now(ZoneInfo('Asia/Makassar')).date()
    result = []
    for row in selected:
        station = stations[row.sid]
        visit = visits.get(row.mid)
        age = (today-row.last_day).days if row.last_day else None
        status = ('belum' if age is None else 'lama' if settings and age > settings.stale_days
                  else 'baru')
        category = next((r for r in matches[row.mid] if r['kind']=='category'),None)
        computed = cell_map[row.mid]
        result.append({'id':station.id,'code':station.code,'name':station.name,
            'unit_id':station.unit_id, 'address':station.address,'brand':station.brand,
            'extra_values':station.extra_values,'power_kva':float(station.power_kva),
            'feeder_id':station.feeder_id,'feeder':feeders[station.feeder_id].name
               if station.feeder_id in feeders else None,
            'measurement_id':row.mid,'measured_on':visit.measured_on.isoformat() if visit else None,
            'session':visit.session if visit else None,'state':visit.state if visit else None,
            'snapshot_power_kva':float(visit.snapshot_power_kva) if visit else None,
            'last_measured_on':row.last_day.isoformat() if row.last_day else None,
            'age_days':age,'status':status,'columns':computed,
            'reference':computed.get(ref.code,{}).get('value') if ref else None,
            'reference_code':ref.code if ref else None,
            'sessions':sessions.get(row.sid,{}),
            'category':category or {'code':'tidak_dapat_dinilai','name':'Tidak dapat dinilai',
                                     'color':'#768994','marker':'circle'},
            'categories':[x for x in matches[row.mid] if x['kind']=='category'],
            'findings':[x for x in matches[row.mid] if x['kind']=='finding'],
            'result_version':marks.get(row.mid), 'stale_result':bool(visit and marks.get(row.mid)!=version),
            'followup':follow.get(row.sid)})
    return result


def _followups(db, station_ids):
    """Most relevant follow-up per gardu: open/working first, then latest finished (9d-3)."""
    from .followup_models import GarduFollowup, GarduFollowupType
    if not station_ids: return {}
    names = {t.code:t.name for t in db.query(GarduFollowupType)}
    rank = {'terbuka':0,'dikerjakan':0,'selesai':1}
    best = {}
    for f in db.query(GarduFollowup).filter(GarduFollowup.substation_id.in_(station_ids),
                                            GarduFollowup.status!='batal'):
        key = (rank.get(f.status,2), -f.id)
        if f.substation_id not in best or key < best[f.substation_id][0]:
            best[f.substation_id] = (key, {'id':f.id,'status':f.status,'type_code':f.type_code,
                'type':names.get(f.type_code,f.type_code),'assignee':f.assignee,
                'due_on':f.due_on.isoformat() if f.due_on else None})
    return {k:v[1] for k,v in best.items()}


def _session_values(db, station_ids, column):
    if not station_ids or not column: return {}
    m = SubstationMeasurement
    ranked = db.query(m.id.label('mid'),m.substation_id.label('sid'),m.session,
        func.row_number().over(partition_by=(m.substation_id,m.session),
            order_by=(m.measured_on.desc(),m.id.desc())).label('rn'))\
        .filter(m.substation_id.in_(station_ids)).subquery()
    found = db.query(ranked.c.sid,ranked.c.session,GarduCalcValue.value)\
        .outerjoin(GarduCalcValue, (GarduCalcValue.measurement_id==ranked.c.mid)
                   & (GarduCalcValue.column_id==column.id)).filter(ranked.c.rn==1).all()
    result=defaultdict(dict)
    for sid,session,value in found: result[sid][session]=value
    return result


def summary(db, filtered):
    """Summary uses precisely the same filtered row relation as the table."""
    subset = filtered.order_by(None).subquery()
    total = db.query(func.count()).select_from(subset).scalar() or 0
    rule_counts = db.query(GarduCalcRule.code, GarduCalcRule.name,
                          GarduCalcRule.kind,GarduCalcRule.group_name,
                          GarduCalcRule.color, func.count().label('count'))\
        .join(GarduCalcMatch, GarduCalcRule.id==GarduCalcMatch.rule_id)\
        .join(subset, GarduCalcMatch.measurement_id==subset.c.mid)\
        .filter(GarduCalcRule.active.is_(True)).group_by(
        GarduCalcRule.id,GarduCalcRule.code,GarduCalcRule.name,GarduCalcRule.kind,
        GarduCalcRule.group_name,GarduCalcRule.color).all()
    grouped = db.query(subset.c.feeder_id, GarduCalcRule.code,
                       func.count().label('count'))\
        .join(GarduCalcMatch, GarduCalcMatch.measurement_id == subset.c.mid)\
        .join(GarduCalcRule, GarduCalcRule.id==GarduCalcMatch.rule_id)\
        .filter(GarduCalcRule.kind=='category',GarduCalcRule.active.is_(True))\
        .group_by(subset.c.feeder_id,GarduCalcRule.code).all()
    counts = {c:count for c,n,k,g,color,count in rule_counts}
    all_rules=db.query(GarduCalcRule).filter_by(active=True).order_by(
        GarduCalcRule.display_order).all()
    categories = [dict(code=r.code,name=r.name,kind=r.kind,group_name=r.group_name,
                       color=r.color,count=counts.get(r.code,0))
                  for r in all_rules if r.kind=='category']
    findings = [dict(code=r.code,name=r.name,kind=r.kind,group_name=r.group_name,
                     color=r.color,count=counts.get(r.code,0))
                for r in all_rules if r.kind=='finding']
    feeder_rows = [{'feeder_id':fid,'category':code,'count':count}
                   for fid,code,count in grouped]
    groups={r['group_name'] for r in categories}
    unknown={group:max(0,total-sum(r['count'] for r in categories
                                   if r['group_name']==group)) for group in groups}
    return {'total':total,'categories':categories,'findings':findings,
            'feeder_categories':feeder_rows, 'unassessed_by_group':unknown,
            'unassessed':sum(unknown.values())}
