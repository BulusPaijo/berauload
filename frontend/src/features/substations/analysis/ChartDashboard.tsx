import {useEffect,useMemo,useRef,useState} from 'react';
import {Bar,BarChart,CartesianGrid,Cell,ComposedChart,Line,ReferenceLine,
 ResponsiveContainer,Scatter,Tooltip,XAxis,YAxis} from 'recharts';
import {api} from '../../../api';
import {encodeCsv,feederStacks,findingPareto,scatterPairs,trendRows} from './chartHelpers.mjs';
import type {AnalysisDefinitions,Summary} from './types';
import './charts.css';

type Charts={summary:Summary;reference_code:string|null;reference_unit:string;
 scatter:{id:number;sessions:Record<string,number|null>}[];pareto:{id:number;value:number}[];
 trend:{day:string;session:string;value:number}[];scatter_truncated:boolean;scatter_total:number};
type Props={query:string;definitions:AnalysisDefinitions;chart:string;onChartChange:(next:string)=>void;
 onPick:(id:number)=>void;fixed?:boolean};
const shared=new Map<string,{at:number;p:Promise<Charts>}>();
function load(url:string){const hit=shared.get(url);if(hit&&Date.now()-hit.at<4000)return hit.p;
 const p=api<Charts>(url);shared.set(url,{at:Date.now(),p});p.catch(()=>shared.delete(url));return p;}
const colors=['#0b8190','#e58a00','#346cad','#9364b3'];
export default function ChartDashboard({query,definitions,chart,onChartChange,onPick,fixed}:Props){
 const [data,setData]=useState<Charts|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 const [station,setStation]=useState(0),[retry,setRetry]=useState(0);const frame=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  let active=true;setLoading(true);
  load(`/substations/analysis/charts?${query}${station?'&station_id='+station:''}`).then(value=>{
   if(active){setData(value);setError('');}}).catch(e=>{if(active)setError(String(e))}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[query,station,retry]);
 const categoryRules=definitions.rules.filter(r=>r.kind==='category');
 const sessions=definitions.sessions.map(s=>s.code);
 const rows=useMemo(()=>{
  if(!data)return [];
  if(chart==='feeder')return feederStacks(data.summary,definitions);
  if(chart==='scatter')return scatterPairs(data.scatter,sessions);
  if(chart==='load_pareto')return data.pareto;
  if(chart==='finding_pareto')return findingPareto(data.summary.findings);
  return trendRows(data.trend);
 },[chart,data,definitions,sessions.join('|')]);
 const title:{[key:string]:string}={feeder:'Sebaran kondisi per penyulang',scatter:'Perbandingan sesi',
  load_pareto:'Pareto kolom acuan',finding_pareto:'Pareto temuan',trend:'Tren pengukuran tersimpan'};
 function csv(){
  const blob=new Blob([encodeCsv(rows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download=`BerauLoad_${chart}.csv`;link.click();URL.revokeObjectURL(url);
 }
 function png(){
  const svg=frame.current?.querySelector('svg.recharts-surface');if(!svg){setError('Grafik belum siap diekspor.');return;}
  const copy=svg.cloneNode(true) as SVGSVGElement,box=svg.getBoundingClientRect();
  copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.setAttribute('width',String(Math.max(700,Math.round(box.width))));copy.setAttribute('height',String(Math.max(300,Math.round(box.height))));
  const img=new Image(),url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));
  img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=Number(copy.getAttribute('width'))*2;canvas.height=Number(copy.getAttribute('height'))*2;
   const ctx=canvas.getContext('2d');if(!ctx)return;ctx.scale(2,2);ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0);
   canvas.toBlob(blob=>{if(!blob)return;const out=URL.createObjectURL(blob),a=document.createElement('a');a.href=out;a.download=`BerauLoad_${chart}.png`;a.click();URL.revokeObjectURL(out);},'image/png');URL.revokeObjectURL(url);};
  img.onerror=()=>{setError('Gambar grafik gagal dibuat. Coba CSV.');URL.revokeObjectURL(url)};img.src=url;
 }
 const max=Math.ceil(Math.max(100,...(data?.scatter??[]).flatMap(p=>sessions.map(s=>p.sessions[s]??0)))/10)*10;
 return <section className={"gardu-chart-card"+(fixed?" is-fixed":"")}><header><div><h3>{title[chart]??title.feeder}</h3><p>{chart==='scatter'?'Titik = gardu; garis diagonal = kedua sesi sama':chart==='trend'?'Rata-rata hasil tersimpan per tanggal dan sesi':'Data mengikuti seluruh filter Analisa, bukan hanya halaman tabel'}</p></div>
 <div className="analysis-actions">{!fixed&&<select aria-label="Jenis grafik" value={chart} onChange={e=>onChartChange(e.target.value)}>{Object.entries(title).map(([code,label])=><option key={code} value={code}>{label}</option>)}</select>}
 {chart==='trend'&&<select aria-label="Tren gardu" value={station} onChange={e=>setStation(Number(e.target.value))}><option value={0}>Semua gardu dalam filter</option>{(data?.pareto??[]).map(p=><option key={p.id} value={p.id}>Gardu #{p.id}</option>)}</select>}
 {fixed?<details className="analysis-menu"><summary className="gardu-chart-more" aria-label="Unduh grafik">⋯</summary><div className="analysis-menu-pop"><button onClick={csv}>Unduh data (CSV)</button><button onClick={png}>Unduh gambar (PNG)</button></div></details>:<><button className="btn secondary sm" onClick={csv}>Unduh CSV</button><button className="btn secondary sm" onClick={png}>Unduh PNG</button></>}</div></header>
 {error&&<div role="alert" className="notice error">{error}<button className="btn secondary sm" onClick={()=>setRetry(v=>v+1)}>Coba lagi</button></div>}
 {loading&&<p role="status">Memuat grafik sesuai filter…</p>}
 {data?.scatter_truncated&&chart==='scatter'&&<p>Grafik menampilkan 2.000 dari {data.scatter_total} titik. Data tidak diinterpolasi.</p>}
 <div className="gardu-chart-plot" ref={frame}>{rows.length?<ResponsiveContainer width="100%" height="100%">{
  chart==='feeder'?<BarChart data={rows} margin={{left:10,right:20,bottom:5}}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="feeder" fontSize={11}/><YAxis fontSize={11}/><Tooltip/>{categoryRules.map(r=><Bar key={r.code} dataKey={r.code} name={r.name} stackId="cats" fill={r.color}/>)}</BarChart>:
  chart==='scatter'?<ComposedChart margin={{left:10,right:25,bottom:10,top:10}}><CartesianGrid strokeDasharray="3 3"/><XAxis type="number" dataKey="x" domain={[0,max]} fontSize={10} name={definitions.sessions[0]?.name}/><YAxis type="number" dataKey="y" domain={[0,max]} fontSize={10} name={definitions.sessions[1]?.name}/><Tooltip cursor={{strokeDasharray:'3 3'}}/><ReferenceLine segment={[{x:0,y:0},{x:max,y:max}]} stroke="#7e929b" strokeDasharray="3 3"/>{data?.reference_unit==='%'&&<><ReferenceLine y={100} stroke="#b62823" strokeDasharray="4 3"/><ReferenceLine x={100} stroke="#b62823" strokeDasharray="4 3"/></>}<Scatter data={rows} fill="#0b8190" onClick={point=>{const p=point as unknown as {id?:number;payload?:{id?:number}};const id=p.payload?.id??p.id;if(id)onPick(id)}}/></ComposedChart>:
  chart==='trend'?<ComposedChart data={rows}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="day" fontSize={10}/><YAxis fontSize={10}/><Tooltip/>{sessions.map((session,i)=><Line key={session} dataKey={session} name={definitions.sessions[i]?.name??session} stroke={colors[i%colors.length]} dot={false} connectNulls={false}/>)}{data?.reference_unit==='%'&&<ReferenceLine y={100} stroke="#b62823" strokeDasharray="4 4"/>}</ComposedChart>:
  <BarChart data={rows} margin={{left:10,right:20,bottom:3}}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey={chart==='finding_pareto'?'name':'id'} fontSize={10}/><YAxis fontSize={10}/><Tooltip/><Bar dataKey={chart==='finding_pareto'?'count':'value'} fill="#0b8190">{rows.map((r,i)=><Cell key={i} fill={chart==='finding_pareto'&&'color' in r?String(r.color):colors[i%colors.length]}/>)}</Bar></BarChart>
 }</ResponsiveContainer>:<div className="gardu-chart-empty">Belum ada hasil hitung yang sesuai untuk grafik ini.</div>}</div>
 </section>;
}
