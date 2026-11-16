import {api,qs} from '../../api';
import type {Status} from '../unit-references/SourceStatus';
import type {DashPanel,PaneContext,LoadedPanel,DataPoint} from './types';

import {applyDisplayUnit} from './unitPresentation';

type ResultRow={period:string;min:number;avg:number;peak:number;count:number};
type BatchResponse={data:Record<string,ResultRow[]>;units:Record<string,string>;source_status?:Status};
type PairRow={period:string;capacity_kw:number|null;paired_load_kw:number|null;paired_hours:number};
type HistoricalResponse={source_status?:Status;data:{period:string;value:number|null;count:number;expected:number;coverage_pct:number}[];result_unit:string};
type RuleResponse={source_status?:Status;status_counts:Record<string,number>;valid_hours:number;expected_hours:number;missing_or_invalid_hours:number};

function slots({start,end,granularity}:PaneContext):string[]{
  const result:string[]=[];
  const current=new Date(`${start}T00:00:00Z`);
  const last=new Date(`${end}T00:00:00Z`);
  while(current<=last&&result.length<1200){
    const day=current.toISOString().slice(0,10);
    if(granularity==='hour'){
      for(let h=0;h<24;h++) result.push(`${day} ${String(h).padStart(2,'0')}:00`);
    }else if(granularity==='day')result.push(day);
    else if(granularity==='month')result.push(day.slice(0,7));
    else result.push(day.slice(0,4));
    if(granularity==='hour'||granularity==='day')current.setUTCDate(current.getUTCDate()+1);
    else if(granularity==='month')current.setUTCMonth(current.getUTCMonth()+1,1);
    else current.setUTCFullYear(current.getUTCFullYear()+1,0,1);
  }
  return [...new Set(result)];
}

function align(rows:DataPoint[],ctx:PaneContext,keys:string[]):DataPoint[]{
  const observed=new Map(rows.map(row=>[row.period,row]));
  return slots(ctx).map(period=>({period,...Object.fromEntries(keys.map(key=>[key,null])),...(observed.get(period)||{})}));
}

async function metricPanel(panel:DashPanel,ctx:PaneContext):Promise<LoadedPanel>{
  const codes=panel.metric_codes;
  const args=qs({start:ctx.start,end:ctx.end,granularity:ctx.granularity});
  const CAP=ctx.catalog.roles?.['system.capacity'];
  const LOAD=ctx.catalog.roles?.['system.load'];
  const paired=Boolean(CAP&&LOAD&&codes.length===2&&codes.includes(CAP)&&codes.includes(LOAD));
  const catalog=ctx.catalog.metrics;
  const series=codes.map(key=>({key,name:catalog.find(m=>m.code===key)?.name||key,unit:catalog.find(m=>m.code===key)?.unit||''}));
  if(paired&&CAP&&LOAD){
    const result=await api<{data:PairRow[]}>(`/monitoring/capacity-vs-load?${args}`);
    const rows:DataPoint[]=result.data.map(r=>({period:r.period,[CAP]:r.paired_hours?r.capacity_kw:null,[LOAD]:r.paired_load_kw,[CAP+'_count']:r.paired_hours,[LOAD+'_count']:r.paired_hours}));
    return {points:align(rows,ctx,codes),series,unit:'kW',coverage:'H/J: hanya pembacaan jam berpasangan; data kosong tetap kosong.'};
  }
  // One grouped request for up to four series. No persistent browser cache:
  // fresh readings are visible as soon as the API cache invalidates on commit.
  const fetched=await api<BatchResponse>(`/performance/series?${args}&codes=${encodeURIComponent(codes.join(','))}`);
  const merged=new Map<string,DataPoint>();
  codes.forEach(code=>(fetched.data[code]||[]).forEach(row=>{
    const current=merged.get(row.period)||{period:row.period};
    current[code]=row[panel.aggregation];
    current[code+'_count']=row.count;
    merged.set(row.period,current);
  }));
  return {points:align([...merged.values()],ctx,codes),series,unit:fetched.units[codes[0]]||'',sourceStatus:fetched.source_status,
    coverage:`${panel.aggregation==='avg'?'Rata-rata':panel.aggregation==='peak'?'Maksimum':'Minimum'} pengukuran tiap interval. Titik kosong tidak diisi nol.`};
}

async function historicalPanel(panel:DashPanel,ctx:PaneContext):Promise<LoadedPanel>{
  const result=await api<HistoricalResponse>(`/historical-calculations/${panel.source_id}/run?${qs({start:ctx.start,end:ctx.end})}`);
  return {points:result.data.map(row=>({period:row.period,value:row.value,count:row.count})),
    series:[{key:'value',name:panel.title,unit:result.result_unit}],unit:result.result_unit,
    sourceStatus:result.source_status,
    coverage:'Hasil formula historis sesuai resolusi yang tersimpan; periode parsial harus diperiksa.'};
}

async function rulePanel(panel:DashPanel,ctx:PaneContext):Promise<LoadedPanel>{
  const result=await api<RuleResponse>(`/engineering-rules/${panel.source_id}/history?${qs({start:ctx.start,end:ctx.end})}`);
  return {points:[],series:[],unit:'jam',rule:result,sourceStatus:result.source_status,
    coverage:'Evaluasi berdasarkan aturan aktif; bukan alarm real-time atau perintah kontrol.'};
}

export async function loadPanel(panel:DashPanel,ctx:PaneContext):Promise<LoadedPanel>{
  if(panel.source==='historical')return historicalPanel(panel,ctx);
  if(panel.source==='engineering')return rulePanel(panel,ctx);
  return applyDisplayUnit(panel,ctx,await metricPanel(panel,ctx));
}
