import {useEffect,useMemo,useState} from 'react';
import {Bar,BarChart,CartesianGrid,Legend,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {Check,ChevronDown,RotateCcw,Save,SlidersHorizontal} from 'lucide-react';
import {api,isoWita,months,num,pct,qs} from '../../api';
import type {Catalog,User} from '../../api';
import './standard-comparison.css';

type Aggregation='max'|'avg'|'min';
type Selection={metric_code:string;aggregation:Aggregation};
type Preference={system:Selection;personal:Selection|null;effective:Selection;source:'system'|'personal'};
type Summary={peak:number;avg:number;min:number;hours:number};
type MonthRow={month:number;a:Summary|null;b:Summary|null;value_a:number|null;value_b:number|null;growth_pct:number|null;comparable:boolean};
type Comparison={year_a:number;year_b:number;metric:string;metric_name:string;unit:string;aggregation:Aggregation;data:MonthRow[]};
const DEFAULT_AGGREGATION:Aggregation='max';
const METHODS:{value:Aggregation;label:string}[]=[
 {value:'max',label:'Maksimum'},{value:'avg',label:'Rata-rata'},{value:'min',label:'Minimum'}
];
const years=Array.from({length:81},(_,i)=>2020+i);
const errorText=(err:unknown)=>err instanceof Error?err.message:String(err);

export default function StandardComparison({catalog,user}:{catalog:Catalog;user:User}){
 const [metric,setMetric]=useState(catalog.roles?.['system.load']||''),[aggregation,setAggregation]=useState<Aggregation>(DEFAULT_AGGREGATION);
 const [yearA,setYearA]=useState(Number(isoWita().slice(0,4))-1),[yearB,setYearB]=useState(Number(isoWita().slice(0,4)));
 const [prefs,setPrefs]=useState<Preference|null>(null),[expanded,setExpanded]=useState(false),[search,setSearch]=useState('');
 const [comparison,setComparison]=useState<Comparison|null>(null),[busy,setBusy]=useState(false);
 const [saving,setSaving]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 const options=useMemo(()=>catalog.metrics.filter(m=>m.active&&m.code!=='daya_mampu_sistem_kw'),[catalog]);
 const visibleOptions=useMemo(()=>options.filter(m=>`${m.name} ${m.code} ${m.unit}`.toLowerCase().includes(search.toLowerCase())),[options,search]);
 const chosen=options.find(m=>m.code===metric);
 const selectedMethod=METHODS.find(m=>m.value===aggregation)?.label||'Maksimum';
 const unsaved=Boolean(prefs && (prefs.effective.metric_code!==metric || prefs.effective.aggregation!==aggregation));
 useEffect(()=>{
  let alive=true;
  api<Preference>('/standard-reports').then(result=>{
   if(!alive)return;
   setPrefs(result);setMetric(result.effective.metric_code||'');setAggregation(result.effective.aggregation);
  }).catch(err=>{if(alive)setError(errorText(err))});
  return()=>{alive=false};
 },[]);
 useEffect(()=>{
  if(!metric)return;
  let alive=true;setBusy(true);setError('');
  api<Comparison>(`/compare?${qs({year_a:yearA,year_b:yearB,metric,aggregate:aggregation})}`)
   .then(result=>{if(alive)setComparison(result)})
   .catch(err=>{if(alive){setComparison(null);setError(errorText(err))}})
   .finally(()=>{if(alive)setBusy(false)});
  return()=>{alive=false};
 },[metric,aggregation,yearA,yearB]);
 async function persist(scope:'mine'|'system'|'reset'){
  setSaving(true);setMessage('');setError('');
  try{
   const result=await api<Preference>(`/standard-reports/${scope==='reset'?'mine':scope}`,
    scope==='reset'?{method:'DELETE'}:{method:'PUT',body:JSON.stringify({metric_code:metric,aggregation})});
   setPrefs(result);
   if(scope==='reset'){setMetric(result.effective.metric_code||'');setAggregation(result.effective.aggregation)}
   setMessage(scope==='system'?'Default sistem diperbarui.':'Pengaturan pilihan berhasil disimpan.');
  }catch(err){setError(errorText(err))}finally{setSaving(false)}
 }
 const chartData=comparison?.data.map(row=>({month:months[row.month-1].slice(0,3),a:row.value_a,b:row.value_b}))||[];
 return <section className="panel std-comparison">
  <div className="std-compare-heading">
   <div><h3>Perbandingan Parameter Antar-Tahun</h3><p className="muted small">Pilih satu parameter dan metode statistik untuk dibandingkan pada 12 bulan.</p></div>
   <div className="period-input std-compare-years">
    <label>Tahun A<select aria-label="Tahun pembanding" value={yearA} onChange={e=>setYearA(Number(e.target.value))}>{years.map(y=><option key={y} value={y}>{y}</option>)}</select></label>
    <span>vs</span>
    <label>Tahun B<select aria-label="Tahun realisasi" value={yearB} onChange={e=>setYearB(Number(e.target.value))}>{years.map(y=><option key={y} value={y}>{y}</option>)}</select></label>
   </div>
  </div>
  <div className="std-compare-summary">
   <div><strong>{chosen?.name||comparison?.metric_name||metric}</strong><small>{selectedMethod} per bulan · {chosen?.unit||comparison?.unit||'—'} · {unsaved?'Pilihan sementara':prefs?.source==='personal'?'Default pribadi':'Default sistem'}</small></div>
   <button className="btn secondary" type="button" onClick={()=>setExpanded(v=>!v)} aria-expanded={expanded}><SlidersHorizontal size={16}/>{expanded?'Tutup Pilihan':'Pilih Parameter'}<ChevronDown size={14}/></button>
  </div>
  {expanded&&<div className="std-compare-picker">
   <div className="std-compare-picker-head"><strong>Parameter yang dibandingkan</strong><span className="muted small">Pilih satu parameter Input atau Computed</span></div>
   <input type="search" aria-label="Cari parameter" placeholder="Cari nama atau kode parameter…" value={search} onChange={e=>setSearch(e.target.value)}/>
   <div className="std-compare-list">
    {visibleOptions.map(p=><label key={p.code} className={metric===p.code?'selected':''}>
     <input type="radio" name="std-comparison-metric" checked={metric===p.code} onChange={()=>setMetric(p.code)}/>
     <span><strong>{p.name}</strong><small>{p.code} · {p.unit} · {p.mode==='computed'?'Computed':'Input/Impor'}</small></span>
    </label>)}
    {!visibleOptions.length&&<div className="muted small">Tidak ada parameter yang cocok.</div>}
   </div>
   <div className="std-compare-actions">
    <label>Metode agregasi<select value={aggregation} onChange={e=>setAggregation(e.target.value as Aggregation)}>{METHODS.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
    <button className="btn secondary" disabled={saving} type="button" onClick={()=>{const s=prefs?.system;setMetric(s?.metric_code||catalog.roles?.['system.load']||'');setAggregation(s?.aggregation||'max')}}><RotateCcw size={15}/> Muat Default Sistem</button>
    <button className="btn primary" disabled={saving||!chosen} type="button" onClick={()=>persist('mine')}><Save size={15}/> Simpan Pilihan Saya</button>
    {prefs?.personal&&<button className="btn secondary" disabled={saving} type="button" onClick={()=>persist('reset')}>Reset Pribadi</button>}
    {user.role==='admin'&&<button className="btn secondary" disabled={saving||!chosen} type="button" onClick={()=>persist('system')}><Check size={15}/> Jadikan Default Sistem</button>}
   </div>
   <p className="muted small">Pilihan parameter dan agregasi dapat disimpan. Tahun yang dipilih hanya untuk analisis saat ini.</p>
  </div>}
  {message&&<p className="std-compare-success" role="status">{message}</p>}
  {error&&<p className="std-compare-error" role="alert">{error}</p>}
  {busy?<div className="std-compare-loading">Memuat perbandingan…</div>:comparison&&<>
   <div className="std-compare-graph"><ResponsiveContainer width="100%" height="100%">
    <BarChart data={chartData} margin={{left:2,right:10,top:12,bottom:2}}>
     <CartesianGrid vertical={false} stroke="#e8eff1"/><XAxis dataKey="month" tickLine={false} axisLine={false}/>
     <YAxis tickLine={false} axisLine={false} tickFormatter={v=>num(Number(v),0)}/>
     <Tooltip formatter={v=>v==null?'—':`${num(Number(v),2)} ${comparison.unit}`} />
     <Legend/><Bar name={String(yearA)} dataKey="a" fill="#153d52" radius={[4,4,0,0]}/>
     <Bar name={String(yearB)} dataKey="b" fill="#00a3a6" radius={[4,4,0,0]}/>
    </BarChart>
   </ResponsiveContainer></div>
   <div className="scroll-table"><table><thead><tr><th>Bulan</th><th>{yearA} ({comparison.unit})</th><th>{yearB} ({comparison.unit})</th><th>Perubahan {selectedMethod}</th><th>Validitas</th></tr></thead>
    <tbody>{comparison.data.map(row=><tr key={row.month}><td>{months[row.month-1]}</td><td className="mono">{num(row.value_a,2)}</td><td className="mono">{num(row.value_b,2)}</td><td>{row.growth_pct==null?'—':pct(row.growth_pct)}</td><td><span className={'tag '+(row.comparable?'success':'warning')}>{row.comparable?'Periode lengkap':'Parsial/tidak ada'}</span></td></tr>)}</tbody>
   </table></div>
   <p className="muted small">Rata-rata menggunakan jam yang tercatat; maksimum/minimum adalah nilai pembacaan pada periode. Persentase tidak dihitung bila tahun pembanding kosong atau bernilai nol. Data parsial hanya indikatif, bukan pertumbuhan YoY resmi.</p>
  </>}
 </section>;
}
