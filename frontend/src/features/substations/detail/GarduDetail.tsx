import {useEffect,useState} from 'react';
import {CartesianGrid,Line,LineChart,ReferenceLine,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,num} from '../../../api';
import type {Definitions} from '../types';
import type {AnalysisDetail} from '../analysis/types';
import {lineTable,mapsLink,phaseBars,trendRows} from './detail.mjs';
import FollowupBox from './FollowupBox';
import AdviceBox from '../advice/AdviceBox';
import './detail.css';

export type DetailStation={id:number;code:string;name:string;feeder:string|null;power_kva:number;unit_id:number;measurement_id:number|null;
 reference:number|null;category:{code:string;name?:string;color?:string;marker?:string};findings?:{code:string;name:string;color:string}[];
 address?:string|null;lat?:number|null;lon?:number|null;line_count?:number};
type Props={station:DetailStation;canInput:boolean;canFollow:boolean;onClose:()=>void;onNavigate:(tab:string,id?:number|string)=>void;onChange?:()=>void};
let defsCache:Promise<Definitions>|null=null;
const SESSION_COLORS=['#0b8190','#de8700','#356aac','#7e55a5'];
const STATS=['beban_kva','tak_seimbang','v_ujung_min'];
export default function GarduDetail({station,canInput,canFollow,onClose,onNavigate,onChange}:Props){
 const [detail,setDetail]=useState<AnalysisDetail|null>(null),[defs,setDefs]=useState<Definitions|null>(null);
 const [trend,setTrend]=useState<{day:string;session:string;value:number}[]>([]),[unit,setUnit]=useState(''),[error,setError]=useState('');
 useEffect(()=>{let live=true;setDetail(null);setTrend([]);setError('');
  defsCache??=api<Definitions>('/substations/definitions');defsCache.then(d=>live&&setDefs(d)).catch(()=>{defsCache=null});
  api<{trend:typeof trend;unit:string}>(`/substations/analysis/stations/${station.id}/trend`).then(r=>{if(live){setTrend(r.trend);setUnit(r.unit??'')}}).catch(()=>{});
  if(station.measurement_id)api<AnalysisDetail>(`/substations/analysis/measurements/${station.measurement_id}`).then(d=>live&&setDetail(d)).catch(e=>live&&setError(String(e)));
  return()=>{live=false};},[station.id,station.measurement_id]);
 const cols=detail?.calculated.columns??[];
 const byCode=Object.fromEntries(cols.map(c=>[c.code,c]));
 const bars=phaseBars(byCode);const nominal=byCode['arus_nominal']?.value;
 const stats=STATS.map(c=>byCode[c]).filter(Boolean);
 const table=defs&&detail?lineTable(defs.params,detail.values):null;
 const t=trendRows(trend);const maps=mapsLink(station.lat,station.lon);
 const color=station.category.color??'#768994';
 const m=detail?.measurement;
 return <div className="gd">
  <header className="gd-head"><div><div className="gd-kicker">Rincian gardu</div><h3>{station.code} · {station.name}</h3>
   <p>{[station.address,station.feeder,`${num(station.power_kva)} kVA`,station.line_count&&`${station.line_count} jurusan`].filter(Boolean).join(' · ')}</p></div>
   <button className="gd-x" aria-label="Tutup rincian" onClick={onClose}>✕</button></header>
  <div className="gd-body">
   <span className="gd-cat" style={{color,background:color+'1c',borderColor:color+'55'}}>{station.category.name??'Tidak dapat dinilai'}{station.reference!=null&&` ${num(station.reference,0)}${unit==='%'?'%':''}`}</span>
   {m&&<p className="gd-muted">Pengukuran {m.measured_on} · {m.session} · {m.state==='verified'?'terverifikasi':'draft'}</p>}
   {!station.measurement_id&&<p className="gd-muted">Gardu ini belum pernah diukur.</p>}
   {error&&<p className="gd-error" role="alert">{error}</p>}
   {!!stats.length&&<div className="gd-stats">{stats.map(s=><div key={s.code}><small>{s.name}</small><b>{s.value==null?'—':`${num(s.value,s.unit==='%'?0:1)}${s.unit==='%'?'%':' '+s.unit}`}</b></div>)}</div>}
   {!!bars.length&&<><h4>Arus per fasa{nominal?` (In ${num(nominal,0)} A)`:''}</h4>
    {bars.map(b=><div key={b.code} className="gd-bar"><span className={'gd-ph gd-ph-'+b.letter}>{b.letter}</span><div className="gd-track"><i className={'gd-fill gd-'+b.tone} style={{width:`${Math.min(100,Math.max(0,b.pct??0))}%`}}/></div><b>{b.value==null?'—':`${num(b.value,0)} A`}</b></div>)}</>}
   {table&&!!table.rows.length&&<><h4>Per jurusan (A){m?` · ${m.session.toLowerCase()} ${m.measured_on}`:''}</h4>
    <table className="gd-table"><thead><tr><th>Jurusan</th>{table.head.map(h=><th key={h}>{h}</th>)}</tr></thead>
     <tbody>{table.rows.map(r=><tr key={r.line}><td>Jurusan {r.line}</td>{r.cells.map((c,i)=><td key={i} className={typeof c==='string'?'gd-flag':''}>{c==null?'—':typeof c==='string'?c:num(c,1)}</td>)}</tr>)}</tbody></table></>}
   {!!station.findings?.length&&<><h4>Temuan</h4><div className="gd-chips">{station.findings.map(f=><span key={f.code} style={{color:f.color,background:f.color+'18'}}>{f.name}</span>)}</div></>}
   {station.category.code==='overload'&&<><h4>Saran penanganan overload</h4><AdviceBox stationId={station.id} measurementId={station.measurement_id} canCreate={canFollow} onChange={onChange}/></>}
   <h4>Tindak lanjut</h4><FollowupBox stationId={station.id} measurementId={station.measurement_id} canEdit={canFollow} onChange={onChange}/>
   <h4>Riwayat {unit==='%'?'% beban':'nilai acuan'}</h4>
   {t.rows.length?<div className="gd-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={t.rows} margin={{top:8,right:12,bottom:0,left:-18}}>
    <CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="day" fontSize={10}/><YAxis fontSize={10}/><Tooltip/>
    {t.sessions.map((s,i)=><Line key={s} dataKey={s} name={s} stroke={SESSION_COLORS[i%4]} strokeDasharray={i?'5 4':undefined} dot={false} connectNulls/>)}
    {unit==='%'&&<ReferenceLine y={100} stroke="#b62823" strokeDasharray="4 4"/>}</LineChart></ResponsiveContainer></div>:<p className="gd-muted">Belum ada riwayat.</p>}
  </div>
  <footer className="gd-foot"><button className="btn primary" disabled={!canInput} title={canInput?'':'Pilih ULP/KP pemilik gardu untuk mengukur'} onClick={()=>onNavigate('mobile',station.id)}>Ukur ulang</button>
   <button className="btn secondary" onClick={()=>onNavigate('visits',station.code)}>Riwayat lengkap</button>
   {maps&&<a className="btn secondary" href={maps} target="_blank" rel="noopener noreferrer">Buka di Google Maps</a>}</footer>
 </div>;
}
