import type {CSSProperties} from 'react';
import {valueText} from './helpers.mjs';
import type {AnalysisDefinitions,AnalysisRow} from './types';

type Ctx={defs:AnalysisDefinitions|null;maxRef:number;refUnit:string;marks:Record<string,string[]>;onOpen:(row:AnalysisRow)=>void};
const FOLLOW:Record<string,string>={terbuka:'fl-open',dikerjakan:'fl-work',selesai:'fl-done'};
export const isNumericColumn=(key:string,defs:AnalysisDefinitions|null)=>key==='power_kva'||key==='reference'||key.startsWith('sesi:')||!!defs?.columns.some(c=>c.code===key);
function bar(value:number|null,max:number,color:string,unit:string){
 const w=value==null?0:Math.min(100,Math.max(0,value/Math.max(max,1)*100));
 return <span className="an-meter"><span className="an-track"><i style={{width:w+'%',background:color}}/></span><b>{valueText(value,0)}{unit==='%'?'%':''}</b></span>;
}
export function renderCell(row:AnalysisRow,key:string,c:Ctx){
 const color=row.category.color;
 if(key==='code')return <button className="an-link" onClick={e=>{e.stopPropagation();c.onOpen(row)}}>{row.code}</button>;
 if(key==='name')return <span className="an-name">{row.name}{row.address&&<small>{row.address}</small>}</span>;
 if(key==='category')return <span className="an-cat" style={{color,background:color+'1a'} as CSSProperties}>{row.category.name}</span>;
 if(key==='findings')return <span className="an-tags">{row.findings.slice(0,2).map(f=><span key={f.code} style={{color:f.color,background:f.color+'16'}}>{f.name}</span>)}{row.findings.length>2&&<span className="an-more">+{row.findings.length-2}</span>}</span>;
 if(key==='reference')return bar(row.reference,c.maxRef,color,c.refUnit);
 if(key.startsWith('sesi:')){const v=row.sessions?.[key.slice(5)]??null;
  const peak=v!=null&&row.reference!=null&&Math.abs(v-row.reference)<1e-9&&Object.keys(row.sessions??{}).length>1;
  return peak?bar(v,c.maxRef,color,c.refUnit):<span className="an-num">{valueText(v,0)}{v!=null&&c.refUnit==='%'?'%':''}</span>;}
 if(key==='followup'){const f=row.followup;
  return f?<span className={'an-follow '+(FOLLOW[f.status]??'')}>{f.type}<small>{f.status}</small></span>:<span className="an-dim">—</span>;}
 const calc=row.columns[key];
 if(calc){const def=c.defs?.columns.find(x=>x.code===key);const hit=(c.marks[key]??[]).some(code=>row.findings.some(f=>f.code===code));
  return <span className={'an-num'+(hit?' an-hit':'')} title={calc.note||''}>{valueText(calc.value,def?.decimals??1,calc.incomplete)}{def?.unit==='%'&&calc.value!=null?'%':''}{hit&&<em aria-label="di luar batas"> ×</em>}</span>;}
 if(key==='power_kva')return valueText(row.power_kva);
 if(key==='measured_on')return row.measured_on?new Date(row.measured_on+'T00:00:00').toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric'}):<span className="an-dim">Belum diukur</span>;
 if(key.startsWith('extra_')){const v=row.extra_values?.[key.slice(6)];return v==null?'—':String(v);}
 if(key==='status')return row.status==='belum'?'Belum diukur':row.status==='lama'?'Perlu diukur ulang':'Terukur';
 const v=row[key as keyof AnalysisRow];return typeof v==='string'||typeof v==='number'?String(v):'—';
}
