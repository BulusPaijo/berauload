import {useEffect,useMemo,useRef,useState} from 'react';
import {Activity,AreaChart as AreaChartIcon,BarChart3,BookOpen,CalendarDays,CheckCircle2,ChevronDown,ChevronRight,ClipboardCheck,Database,Download,FileSpreadsheet,Filter,Gauge,LayoutDashboard,LoaderCircle,LogOut,Menu,PlugZap,RefreshCw,Save,Search,Settings2,ShieldCheck,Upload,Users,AudioLines,X,AlertCircle,Network,TableProperties} from 'lucide-react';
import {AreaChart,Area,BarChart,Bar,CartesianGrid,Legend,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,downloadApi,setCSRF,setActiveUnit,unitCacheKey,isoWita,months,num,pct,qs} from './api';
import UnitSelector from './features/org-units/UnitSelector';
import {useBranding} from './features/branding/BrandingContext';
import BrandMark from './features/branding/BrandMark';
import BrandingSettings from './features/branding/BrandingSettings';
import {safeBrandSlug} from './features/branding/branding.mjs';
import {canWrite,isRootOnly,viewModeLabel,rootDataHint,flattenUnits,type UnitNode} from './features/org-units/unitSelection.mjs';
import useActiveUnit from './features/org-units/useActiveUnit';
import type {User,Catalog,Metric,Dashboard,DayData,Series,Point} from './api';
import ParameterManager from './features/parameters/ParameterManager';
import OrgUnitManager from './features/org-units/OrgUnitManager';
import UserManager from './features/users/UserManager';
import SessionBanner from './features/input-form/autosave/SessionBanner';
import {hasDirty} from './features/input-form/autosave/sessionActivity.mjs';
import PrimaryMetricSettings from './features/primary-metrics/PrimaryMetricSettings';
import TemplateImportPage from './features/template-import/TemplateImportPage';
import AssetManager from './features/assets/AssetManager';
import EquipmentKinds from './features/equipment-kinds/EquipmentKinds';
import UnitManager from './features/units/UnitManager';
import HistoricalCalculations from './features/historical/HistoricalCalculations';
import EngineeringRules from './features/engineering/EngineeringRules';
import DashboardBuilder from './features/dashboard-builder/DashboardBuilder';
import DashboardHome from './features/dashboard-builder/DashboardHome';
import HelpPage from './features/help/HelpPage';
import SystemLoadCompare from './features/monitoring/SystemLoadCompare';
import InputPage from './features/input-form/InputPage';
import InputFormEditor from './features/input-form/InputFormEditor';
import ExportBuilder from './features/data-export/ExportBuilder';
import ReportBuilder from './features/report-builder/ReportBuilder';
import StandardComparison from './features/standard-reports/StandardComparison';
import TopologyPage from './features/topology/TopologyPage';
import type {DiagramNav} from './features/topology/TopologyPage';
import UnitCompleteness from './features/completeness/UnitCompleteness';
import SubstationsPage from './features/substations/SubstationsPage';

const navigation=[
  {key:'dashboard',label:'Dashboard',icon:LayoutDashboard,group:'MONITORING'},
  {key:'builder',label:'Dashboard Builder',icon:BarChart3,group:'MONITORING'},
  {key:'topology',label:'Topologi',icon:Network,group:'MONITORING'},
  {key:'completeness',label:'Kelengkapan Unit',icon:TableProperties,group:'MONITORING'},
  {key:'input',label:'Input Beban Harian',icon:ClipboardCheck,group:'OPERASIONAL'},
  {key:'substations',label:'Pengukuran Gardu',icon:TableProperties,group:'OPERASIONAL'},
  {key:'history',label:'Data Historis',icon:Database,group:'OPERASIONAL'},
  {key:'analytics',label:'Analisis Beban',icon:AreaChartIcon,group:'ANALISIS'},
  {key:'plants',label:'Pembangkit',icon:PlugZap,group:'ANALISIS'},
  {key:'feeders',label:'Monitoring Feeder',icon:Activity,group:'ANALISIS'},
  {key:'reports',label:'Laporan & Perbandingan',icon:BookOpen,group:'PELAPORAN'},
  {key:'export',label:'Export Data Excel / CSV',icon:Download,group:'PELAPORAN'},
  {key:'imports',label:'Import Excel',icon:FileSpreadsheet,group:'PELAPORAN'},
  {key:'settings',label:'Pengaturan',icon:Settings2,group:'SISTEM'},
  {key:'help',label:'Panduan Pengguna',icon:BookOpen,group:'BANTUAN'},
] as const;
type Page=typeof navigation[number]['key'];
function route():Page {const hash=window.location.hash.replace('#/','');return navigation.some(n=>n.key===hash)?hash as Page:'dashboard';}
function go(key:Page){window.location.hash='/'+key;}
function errMessage(e:unknown){return e instanceof Error?e.message:String(e);}
function Panel({children,title,aside}:{children:React.ReactNode,title?:string,aside?:React.ReactNode}){return <section className="panel"><div className="panel-head">{title&&<h3>{title}</h3>}{aside}</div>{children}</section>}
function Notice({children,type='info'}:{children:React.ReactNode,type?:'info'|'error'|'success'}){return <div className={'notice '+type}><AlertCircle size={17}/><span>{children}</span></div>}
function Loading(){return <div className="loading"><LoaderCircle className="spin" size={30}/><span>Memuat data...</span></div>}
function Period({year,setYear,month,setMonth}:{year:number,setYear:(n:number)=>void,month:number,setMonth:(n:number)=>void}){return <div className="period-input"><select value={month} onChange={e=>setMonth(Number(e.target.value))}>{months.map((m,i)=><option value={i+1} key={m}>{m}</option>)}</select><select value={year} onChange={e=>setYear(Number(e.target.value))}>{Array.from({length:18},(_,i)=>2020+i).map(y=><option key={y}>{y}</option>)}</select></div>}
function MetricPicker({metrics,value,onChange,filter}:{metrics:Metric[],value:string,onChange:(v:string)=>void,filter?:string}){return <select value={value} onChange={e=>onChange(e.target.value)}>{metrics.filter(m=>m.active&&(!filter||m.group===filter)).map(m=><option key={m.code} value={m.code}>{m.name} · {m.unit}</option>)}</select>}
function Trend({points,dataKey='peak',unit='kW',height=280,color='#087f8c'}:{points:Point[],dataKey?:'peak'|'avg'|'min',unit?:string,height?:number,color?:string}){return <div style={{width:'100%',height}}><ResponsiveContainer><AreaChart data={points} margin={{top:8,right:20,left:0,bottom:0}}><defs><linearGradient id={'chart'+dataKey} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={color} stopOpacity={0.22}/><stop offset="1" stopColor={color} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e7eef0"/><XAxis dataKey="period" tick={{fontSize:11,fill:'#77919a'}} tickLine={false} axisLine={false} minTickGap={20}/><YAxis tick={{fontSize:11,fill:'#77919a'}} tickLine={false} axisLine={false} width={58} tickFormatter={v=>num(Number(v),0)}/><Tooltip formatter={v=>[`${num(Number(v),2)} ${unit}`,dataKey==='peak'?'Puncak':dataKey==='avg'?'Rata-rata':'Minimum']} contentStyle={{borderRadius:12,border:'1px solid #e4eef0'}}/><Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.5} fill={`url(#chart${dataKey})`} dot={points.length<=15} connectNulls={false}/></AreaChart></ResponsiveContainer></div>}

function Login({onLogin}:{onLogin:(u:User)=>void}){
 const {branding}=useBranding();
 const [username,setUsername]=useState('admin'),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await api<{user:User,csrf:string}>('/auth/login',{method:'POST',body:JSON.stringify({username,password})});setCSRF(r.csrf);onLogin(r.user);}catch(e){setError(errMessage(e));}finally{setBusy(false)}}
 return <div className="login-bg"><div className="login-deco deco1"/><div className="login-deco deco2"/><form onSubmit={submit} className="login-card"><BrandMark login/><div className="eyebrow">{branding.login_eyebrow}</div><h1>{branding.login_welcome}<br/><span>{branding.app_name}</span></h1><p>{branding.login_description}</p><label>Username<input autoFocus value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" required/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/></label>{error&&<Notice type="error">{error}</Notice>}<button className="btn primary login-btn" disabled={busy}>{busy?'Memverifikasi...':branding.login_button_text}<ChevronRight size={18}/></button><small>{branding.login_footnote}</small></form></div>;
}

function DashboardPage({catalog,user}:{catalog:Catalog,user:User}){
 const today=isoWita();const [year,setYear]=useState(Number(today.slice(0,4))),[month,setMonth]=useState(Number(today.slice(5,7)));
 const [data,setData]=useState<Dashboard|null>(null),[busy,setBusy]=useState(true),[error,setError]=useState('');
 useEffect(()=>{let alive=true;setBusy(true);api<Dashboard>(`/dashboard?${qs({year,month})}`).then(r=>{if(alive){setData(r);setError('')}}).catch(e=>{if(alive)setError(errMessage(e))}).finally(()=>{if(alive)setBusy(false)});return()=>{alive=false}},[year,month]);
 const values=data?.daily.map(d=>({period:d.date.slice(8),peak:d.peak_kw,avg:d.avg_kw,min:0,count:d.count}))||[];
 const cards=[{label:'Beban Puncak',value:data?.peak_kw==null?'—':`${num(data.peak_kw/1000,2)} MW`,sub:data?.peak_at||'Belum ada data',icon:Gauge},{label:'Rata-rata Beban',value:data?.avg_kw==null?'—':`${num(data.avg_kw/1000,2)} MW`,sub:'Dari jam yang tercatat',icon:Activity},{label:'Jam Tercatat',value:num(data?.readings_count),sub:`Dari ${num(data?.expected_hours_to_date,0)} jam s.d. hari ini`,icon:CalendarDays},{label:'Cakupan Data',value:pct(data?.coverage_pct),sub:`${data?.final_days||0} hari final`,icon:ShieldCheck}];
 return <div className="page-space">{!catalog.roles?.['system.load']&&<Notice type="info">Parameter utama belum diatur. {user.role==='admin'&&<a href="#/settings">Buka Pengaturan → Parameter utama unit</a>}</Notice>}<div className="page-top"><div><div className="eyebrow">RINGKASAN OPERASIONAL</div><h2>Dashboard Beban Sistem</h2><p>Gambaran sistem kelistrikan Berau dari data historis terpilih.</p></div><Period year={year} setYear={setYear} month={month} setMonth={setMonth}/></div>{error&&<Notice type="error">{error}</Notice>}{busy?<Loading/>:<><div className="kpi-grid">{cards.map((c,i)=><div className="kpi-card" key={c.label}><div className="kpi-icon"><c.icon size={22}/></div><div className="kpi-title">{c.label}</div><div className="kpi-value">{c.value}</div><div className="kpi-sub">{c.sub}</div>{i===3&&<div className="progress-track"><div style={{width:`${Math.min(100,data?.coverage_pct||0)}%`}}/></div>}</div>)}</div><SystemLoadCompare year={year} month={month} catalog={catalog} user={user}/><div className="two-col primary-grid"><Panel title="Kurva Puncak Beban Harian" aside={<span className="pill">{months[month-1]} {year}</span>}>{values.length?<Trend points={values} unit="kW" height={320}/>:<div className="empty">Belum ada data pengukuran pada bulan ini.</div>}<div className="chart-note">Nilai kosong tidak dianggap nol. Grafik bukan monitoring SCADA real-time.</div></Panel><Panel title="Kelengkapan Data"><div className="coverage-figure"><strong>{pct(data?.coverage_pct)}</strong><span>Jam dengan pembacaan beban sistem</span></div><div className="progress-track tall"><div style={{width:`${Math.min(100,data?.coverage_pct||0)}%`}}/></div><div className="stats-list"><div><span>Pengukuran masuk</span><b>{num(data?.readings_count,0)} jam</b></div><div><span>Jam yang diharapkan*</span><b>{num(data?.expected_hours_to_date,0)} jam</b></div><div><span>Hari berstatus final</span><b>{data?.final_days||0} hari</b></div></div><div className="chart-note">* Sampai tanggal hari ini (WITA) atau akhir periode, bukan otomatis 24 jam terakhir.</div></Panel></div><Panel title="Rekap Harian" aside={<button className="btn secondary sm" onClick={()=>go('history')}>Lihat historis <ChevronRight size={14}/></button>}><div className="scroll-table"><table><thead><tr><th>Tanggal</th><th>Beban Puncak</th><th>Rata-rata</th><th>Jam Terisi</th><th>Kelengkapan</th></tr></thead><tbody>{data?.daily.map(d=><tr key={d.date}><td><button className="link-btn" onClick={()=>{sessionStorage.setItem(unitCacheKey('berauload_day'),d.date);go('input')}}>{d.date}</button></td><td className="mono">{num(d.peak_kw,2)} kW</td><td className="mono">{num(d.avg_kw,2)} kW</td><td>{d.count}/24</td><td><span className={'tag '+(d.count===24?'success':'warning')}>{d.count===24?'Lengkap':'Parsial'}</span></td></tr>)}</tbody></table>{!data?.daily.length&&<div className="empty">Belum ada rekap harian.</div>}</div></Panel></>}</div>
}


function HistoryPage(){
 const today=isoWita();const [year,setYear]=useState(Number(today.slice(0,4))),[month,setMonth]=useState(Number(today.slice(5,7)));
 const [data,setData]=useState<Series|null>(null),[error,setError]=useState('');
 useEffect(()=>{const start=`${year}-${String(month).padStart(2,'0')}-01`;const end=new Date(Date.UTC(year,month,0)).toISOString().slice(0,10);api<Series>(`/analytics?${qs({granularity:'day',start,end})}`).then(setData).catch(e=>setError(errMessage(e)))},[year,month]);
 const totalDays=new Date(Date.UTC(year,month,0)).getUTCDate();const lookup=new Map((data?.data||[]).map(d=>[d.period,d]));
 return <div className="page-space"><div className="page-top"><div><div className="eyebrow">ARSIP TERPUSAT</div><h2>Data Historis</h2><p>Buka data hari apa pun tanpa mencari workbook Excel bulanan.</p></div><Period year={year} setYear={setYear} month={month} setMonth={setMonth}/></div>{error&&<Notice type="error">{error}</Notice>}<Panel title={`Kalender Pembacaan · ${months[month-1]} ${year}`}><div className="days-grid">{Array.from({length:totalDays},(_,i)=>{const day=`${year}-${String(month).padStart(2,'0')}-${String(i+1).padStart(2,'0')}`;const point=lookup.get(day);return <button key={day} className={'day-tile '+(point?.count===24?'complete':point?'partial':'empty-day')} onClick={()=>{sessionStorage.setItem(unitCacheKey('berauload_day'),day);go('input')}}><strong>{i+1}</strong><span>{point?`${point.count}/24 jam`:'Kosong'}</span><small>{point?`${num(point.peak/1000,2)} MW`:'—'}</small></button>})}</div><div className="legend"><span><i className="dot green"/> Lengkap</span><span><i className="dot amber"/> Parsial</span><span><i className="dot gray"/> Belum ada data</span></div></Panel></div>
}

function AnalyticsPage({catalog,lockedGroup,user}:{catalog:Catalog,lockedGroup?:string,user?:User}){
 const today=isoWita();const [metric,setMetric]=useState(lockedGroup==='FEEDER'?'feeder_1_r_a':lockedGroup==='PEMBANGKIT'?'pltu_lati_cb33_kw':catalog.roles?.['system.load']||'');
 const [analysisView,setAnalysisView]=useState<'readings'|'historical'|'rules'>('readings');
 const [granularity,setGranularity]=useState('day');const [start,setStart]=useState(today.slice(0,8)+'01'),[end,setEnd]=useState(today);
 const [data,setData]=useState<Series|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const metrics=catalog.metrics.filter(m=>m.active&&(!lockedGroup||m.group===lockedGroup));
 useEffect(()=>{if(!metrics.some(m=>m.code===metric)&&metrics[0])setMetric(metrics[0].code)},[lockedGroup]);
 useEffect(()=>{let alive=true;setBusy(true);api<Series>(`/analytics?${qs({metric,granularity,start,end})}`).then(r=>{if(alive){setData(r);setError('')}}).catch(e=>{if(alive)setError(errMessage(e))}).finally(()=>{if(alive)setBusy(false)});return()=>{alive=false}},[metric,granularity,start,end]);
 const heading=lockedGroup==='FEEDER'?'Monitoring Feeder':lockedGroup==='PEMBANGKIT'?'Monitoring Pembangkit':'Analisis Beban';
 const selected=metrics.find(m=>m.code===metric);
 if (!lockedGroup && analysisView === 'rules') return <div className="page-space"><div className="page-top"><div><div className="eyebrow">ANALISIS DATA HISTORIS</div><h2>Engineering Rules</h2><p>Status teknis berdasarkan aturan yang disetujui.</p></div></div><div className="tabstrip floating"><button onClick={()=>setAnalysisView('readings')}>Analisis Beban</button><button onClick={()=>setAnalysisView('historical')}>Perhitungan Historis</button><button className="active">Engineering Rules</button></div>{user && <EngineeringRules catalog={catalog} user={user}/>}</div>;
 if (!lockedGroup && analysisView === 'historical') return <div className="page-space">
  <div className="page-top"><div><div className="eyebrow">ANALISIS DATA HISTORIS</div><h2>Perhitungan Historis</h2><p>Susun dan jalankan perhitungan per jam, bulan, atau tahun.</p></div></div>
  <div className="tabstrip floating"><button onClick={()=>setAnalysisView('readings')}>Analisis Beban</button><button className="active">Perhitungan Historis</button><button onClick={()=>setAnalysisView('rules')}>Engineering Rules</button></div>
  {user && <HistoricalCalculations catalog={catalog} user={user}/>}</div>;
 return <div className="page-space"><div className="page-top"><div><div className="eyebrow">ANALISIS DATA HISTORIS</div><h2>{heading}</h2><p>Eksplorasi parameter pengukuran melalui rentang waktu yang fleksibel.</p></div></div>{!lockedGroup&&<div className="tabstrip floating"><button className="active">Analisis Beban</button><button onClick={()=>setAnalysisView('historical')}>Perhitungan Historis</button><button onClick={()=>setAnalysisView('rules')}>Engineering Rules</button></div>}<div className="filter-bar"><div className="field grow"><label>Parameter</label><MetricPicker metrics={metrics} value={metric} onChange={setMetric}/></div><div className="field"><label>Resolusi</label><select value={granularity} onChange={e=>setGranularity(e.target.value)}><option value="hour">Per Jam</option><option value="day">Harian</option><option value="month">Bulanan</option><option value="year">Tahunan</option></select></div><div className="field"><label>Mulai</label><input type="date" value={start} onChange={e=>setStart(e.target.value)}/></div><div className="field"><label>Sampai</label><input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></div></div>{error&&<Notice type="error">{error}</Notice>}{busy?<Loading/>:<><div className="kpi-grid three"><div className="kpi-card"><div className="kpi-title">Puncak Tertinggi</div><div className="kpi-value">{num(data?.data.length?Math.max(...data.data.map(d=>d.peak)):null,2)}</div><div className="kpi-sub">{selected?.unit}</div></div><div className="kpi-card"><div className="kpi-title">Minimum Terendah</div><div className="kpi-value">{num(data?.data.length?Math.min(...data.data.map(d=>d.min)):null,2)}</div><div className="kpi-sub">{selected?.unit}</div></div><div className="kpi-card"><div className="kpi-title">Titik Pengamatan</div><div className="kpi-value">{num(data?.data.reduce((a,b)=>a+b.count,0),0)}</div><div className="kpi-sub">Jumlah data valid yang tersedia</div></div></div><Panel title={`${selected?.name||'Parameter'} · Tren ${granularity}`}><Trend points={data?.data||[]} height={360} unit={selected?.unit||''}/>{!data?.data.length&&<div className="empty">Belum ada pembacaan dalam rentang ini.</div>}</Panel><Panel title="Tabel Statistik Per Periode"><div className="scroll-table"><table><thead><tr><th>Periode</th><th>Minimum</th><th>Rata-rata</th><th>Puncak</th><th>Jumlah Pembacaan</th></tr></thead><tbody>{data?.data.map(r=><tr key={r.period}><td>{r.period}</td><td className="mono">{num(r.min,3)}</td><td className="mono">{num(r.avg,3)}</td><td className="mono">{num(r.peak,3)}</td><td>{r.count}</td></tr>)}</tbody></table></div></Panel></>}</div>
}

function ReportsPage({catalog,user}:{catalog:Catalog;user:User}){
 const {branding}=useBranding();
 const [reportMode,setReportMode]=useState<'standard'|'custom'>('standard');
 const today=isoWita();
 const [start,setStart]=useState(today.slice(0,8)+'01'),[end,setEnd]=useState(today);
 if(reportMode==='custom')return <div className="page-space"><div className="tabstrip floating"><button onClick={()=>setReportMode('standard')}>Laporan Standar</button><button className="active">Laporan Kustom</button></div><ReportBuilder catalog={catalog} user={user}/></div>;
 return <div className="page-space">
  <div className="tabstrip floating"><button className="active">Laporan Standar</button><button onClick={()=>setReportMode('custom')}>Laporan Kustom</button></div>
  <div className="page-top"><div><div className="eyebrow">LAPORAN MANAJEMEN</div><h2>Laporan & Perbandingan</h2><p>Unduh data historis dan bandingkan parameter dari tahun ke tahun.</p></div></div>
  <Panel title="Export Excel Historis"><div className="export-row">
   <div className="field"><label>Mulai</label><input type="date" value={start} onChange={e=>setStart(e.target.value)}/></div>
   <div className="field"><label>Sampai</label><input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></div>
   <button className="btn primary" onClick={()=>downloadApi(`/reports/export?${qs({start,end})}`,`${safeBrandSlug(branding.app_short_name)}_${start}_${end}.xlsx`).catch(e=>window.alert(errMessage(e)))}><Download size={16}/> Unduh Excel</button>
   <button className="btn secondary" onClick={()=>downloadApi(`/reports/pdf?${qs({start,end})}`,`${safeBrandSlug(branding.app_short_name)}_${start}_${end}.pdf`).catch(e=>window.alert(errMessage(e)))}><Download size={16}/> Unduh PDF</button>
  </div><p className="muted small">Export maksimum 367 hari, berisi pengukuran per jam dan rekap harian. File laporan sumber asli tetap tersimpan di arsip import.</p></Panel>
  <StandardComparison catalog={catalog} user={user}/>
 </div>;
}

const monthPattern:Record<string,number>={januari:1,februari:2,maret:3,april:4,mei:5,juni:6,juli:7,agustus:8,september:9,oktober:10,november:11,desember:12,jan:1,feb:2,mar:3,apr:4,jun:6,jul:7,agu:8,sep:9,okt:10,nov:11,des:12};
function detectPeriod(filename:string,fallbackYear:number,fallbackMonth:number){const str=filename.toLowerCase();const y=str.match(/20\d{2}/);let month=fallbackMonth;for(const [key,value] of Object.entries(monthPattern)){if(str.includes(key)){month=value;break}}return {year:y?Number(y[0]):fallbackYear,month}}
type Preview={name:string;token:string;period:string;hours_found:number;readings_found:number;existing_hour_conflicts:number;duplicate_file:boolean;warnings:string[];result?:string;error?:string};
function LegacyImportsPage({user}:{user:User}){
 const today=isoWita();const [year,setYear]=useState(Number(today.slice(0,4))),[month,setMonth]=useState(Number(today.slice(5,7)));
 const [files,setFiles]=useState<File[]>([]),[previews,setPreviews]=useState<Preview[]>([]),[history,setHistory]=useState<any[]>([]),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 const editable=['admin','operator','verifier'].includes(user.role);
 function load(){api<any[]>('/imports').then(setHistory).catch(()=>{})}
 useEffect(()=>{load()},[]);
 async function previewAll(){setError('');setMessage('');setPreviews([]);setBusy(true);const result:Preview[]=[];
  for(const file of files){const period=detectPeriod(file.name,year,month);const form=new FormData();form.append('file',file);form.append('year',String(period.year));form.append('month',String(period.month));
   try{const r=await api<any>('/imports/preview',{method:'POST',body:form});result.push({...r,name:file.name})}catch(e){result.push({name:file.name,token:'',period:`${period.year}-${period.month}`,hours_found:0,readings_found:0,existing_hour_conflicts:0,duplicate_file:false,warnings:[],error:errMessage(e)})}
  }setPreviews(result);setBusy(false);
 }
 async function commitAll(){setBusy(true);const list=[...previews];let ok=0;
 for(let i=0;i<list.length;i++){const r=list[i];if(!r.token||r.error||r.duplicate_file)continue;
  try{const done=await api<any>('/imports/commit',{method:'POST',body:JSON.stringify({token:r.token})});list[i]={...r,result:`${done.hours_created} jam baru, ${done.hours_skipped} jam dilewati`};ok++}catch(e){list[i]={...r,error:errMessage(e)}}setPreviews([...list])}
 setBusy(false);setMessage(`${ok} file berhasil diproses.`);load()}
 return <div className="page-space"><div className="page-top"><div><div className="eyebrow">MIGRASI ARSIP</div><h2>Import Excel Historis</h2><p>Ambil data bertahun-tahun dari template laporan beban bulanan.</p></div></div>{error&&<Notice type="error">{error}</Notice>}{message&&<Notice type="success">{message}</Notice>}<Panel title="Unggah Laporan Beban"><div className="upload-zone"><Upload size={35}/><h3>File Excel bulanan (.xlsx)</h3><p>Bisa pilih banyak file sekaligus. Periode otomatis dibaca dari nama file (contoh: NOVEMBER 2026).</p><input type="file" accept=".xlsx" multiple disabled={!editable||busy} onChange={e=>{setFiles(Array.from(e.target.files||[]));setPreviews([])}}/><span>{files.length?`${files.length} file dipilih`:'Maksimal 15 MB per file'}</span></div><div className="import-actions"><div className="field"><label>Tahun fallback</label><select value={year} onChange={e=>setYear(Number(e.target.value))}>{Array.from({length:18},(_,i)=>2020+i).map(y=><option key={y}>{y}</option>)}</select></div><div className="field"><label>Bulan fallback</label><select value={month} onChange={e=>setMonth(Number(e.target.value))}>{months.map((v,i)=><option value={i+1} key={v}>{v}</option>)}</select></div><button className="btn primary" disabled={!editable||busy||!files.length} onClick={previewAll}>{busy?'Memproses...':'Periksa File & Data'}<ChevronRight size={16}/></button></div><div className="chart-note">Pilih periode dengan benar untuk file yang nama bulannya tidak standar. Import tidak akan mengganti jam yang sudah ada, bahkan jika statusnya masih draft.</div></Panel>
 {!!previews.length&&<Panel title="Hasil Pratinjau"><div className="scroll-table"><table><thead><tr><th>Nama File</th><th>Periode</th><th>Jam</th><th>Nilai</th><th>Konflik</th><th>Status</th></tr></thead><tbody>{previews.map((p,i)=><tr key={i}><td>{p.name}</td><td>{p.period}</td><td>{p.hours_found}</td><td>{p.readings_found}</td><td>{p.existing_hour_conflicts}</td><td>{p.error?<span className="tag danger">{p.error}</span>:p.result?<span className="tag success">{p.result}</span>:p.duplicate_file?<span className="tag warning">Sudah diimport</span>:<span className="tag info">Siap diimport</span>}{p.warnings.length>0&&<div className="muted small">{p.warnings.slice(0,2).join('; ')}</div>}</td></tr>)}</tbody></table></div><div className="action-footer"><button className="btn primary" onClick={commitAll} disabled={busy||!previews.some(p=>p.token&&!p.error&&!p.result&&!p.duplicate_file)}><Database size={16}/> Simpan Data yang Baru</button></div></Panel>}
 <Panel title="Riwayat Import"><div className="scroll-table"><table><thead><tr><th>Waktu</th><th>File Asal</th><th>Periode</th><th>Jam Baru</th><th>Dilewati</th><th>Arsip</th></tr></thead><tbody>{history.map(r=><tr key={r.id}><td>{r.created_at?.slice(0,19).replace('T',' ')}</td><td>{r.filename}</td><td>{r.year}-{String(r.month).padStart(2,'0')}</td><td>{r.hours_created}</td><td>{r.hours_skipped}</td><td>{['admin','verifier'].includes(user.role)&&<button className="link-btn" onClick={()=>downloadApi(`/imports/${r.id}/source`,r.filename).catch(e=>window.alert(errMessage(e)))}>Excel asli</button>}</td></tr>)}</tbody></table>{!history.length&&<div className="empty">Belum ada arsip import.</div>}</div></Panel></div>
}

function ImportsPage({user}:{user:User}){
 const {branding}=useBranding();
 const [tab,setTab]=useState<'template'|'legacy'>('template');
 return <div className="page-space"><div className="import-actions">
  <button className={'btn '+(tab==='template'?'primary':'')} onClick={()=>setTab('template')}>Template {branding.app_short_name}</button>
  <button className={'btn '+(tab==='legacy'?'primary':'')} onClick={()=>setTab('legacy')}>Laporan lama</button>
 </div>{tab==='template'?<TemplateImportPage/>:<LegacyImportsPage user={user}/>}</div>
}

function SettingsPage({catalog,refreshCatalog,user,version}:{catalog:Catalog,refreshCatalog:()=>void,user:User,version:string}){
 const {branding}=useBranding();
 const [tab,setTab]=useState(()=>{const t=sessionStorage.getItem('berauload_settings_tab');sessionStorage.removeItem('berauload_settings_tab');return t||'overview'});
 const [logs,setLogs]=useState<any[]>([]);
 useEffect(()=>{if(user.role==='admin')api<any[]>('/audit').then(setLogs).catch(()=>{})},[user.role]);
 return <div className="page-space"><div className="page-top"><div><div className="eyebrow">KONFIGURASI SISTEM</div><h2>Pengaturan</h2><p>Master peralatan, parameter, pengguna dan riwayat aktivitas.</p></div></div>{user.role!=='admin'?<Notice>Pengaturan administratif hanya dapat diubah oleh admin.</Notice>:<><div className="settings-navigation">
 {[["PENGATURAN TAMPILAN",[['overview','Mulai di sini'],['form','Tab & Kolom Input'],['builder','Dashboard Builder']]],
    ["MASTER DATA",[['kinds','Jenis Peralatan'],['assets','Master Peralatan'],['units','Master Satuan'],['metrics','Parameter'],['primary','Parameter utama unit']]],
    ["ADMINISTRASI",[['org','Struktur Organisasi'],['users','Pengguna'],['branding','Branding'],['audit','Audit Log']]]].map(([heading,options])=><div key={String(heading)}>
  <div className="settings-section-title">{String(heading)}</div><div className="settings-nav-links">
  {(options as string[][]).map(([key,label])=><button key={key} className={tab===key?'active':''} onClick={()=>key==='builder'?go('builder'):setTab(key)}>{label}</button>)}
  </div></div>)}
 </div>
 {tab==='overview'&&<section className="panel settings-overview"><h3>Mulai dari mana?</h3><p className="muted">Ikuti urutan ini ketika menyiapkan pencatatan baru. Operator hanya perlu menggunakan menu Input Beban Harian.</p>
  <div className="settings-steps">{[['1','Jenis Peralatan','Atur kategori peralatan terlebih dahulu.','kinds'],['2','Master Peralatan','Daftarkan unit dan feeder aktif.','assets'],['3','Master Satuan','Pilih satuan standar atau tambah satuan custom.','units'],['4','Buat Parameter','Pilih jenis Input untuk pencatatan; Computed untuk hasil rumus.','metrics'],['5','Atur Tab Formulir','Tentukan tab, urutan kolom, dan parameter yang tampil.','form'],['6','Atur Dashboard','Pilih grafik dan panel yang dibutuhkan pengguna.','builder']].map(([step,title,description,destination])=><button key={step} onClick={()=>destination==='builder'?go('builder'):setTab(destination)}><b>{step}</b><span><strong>{title}</strong><small>{description}</small></span><ChevronRight size={16}/></button>)}</div>
 </section>}
 {tab==='org'&&<OrgUnitManager/>}{tab==='branding'&&<BrandingSettings/>}
 {tab==='primary'&&<PrimaryMetricSettings catalog={catalog} refreshCatalog={refreshCatalog}/>} 
 {tab==='units'&&<UnitManager/>}
 {tab==='form'&&<InputFormEditor catalog={catalog}/>}
 {tab==='assets'&&<AssetManager catalog={catalog} refreshCatalog={refreshCatalog}/>}
{tab==='kinds'&&<EquipmentKinds catalog={catalog}/>} {tab==='metrics'&&<ParameterManager catalog={catalog} refreshCatalog={refreshCatalog}/>}{tab==='users'&&<UserManager/>}{tab==='audit'&&<Panel title="Aktivitas Terbaru"><div className="scroll-table"><table><thead><tr><th>Waktu</th><th>User ID</th><th>Aksi</th><th>Target</th><th>Detail</th></tr></thead><tbody>{logs.map((v,i)=><tr key={i}><td>{v.at?.slice(0,19)}</td><td>{v.user_id}</td><td>{v.action}</td><td>{v.target}</td><td className="muted small">{JSON.stringify(v.detail).slice(0,120)}</td></tr>)}</tbody></table></div></Panel>}</>}<Panel title="Informasi Sistem"><div className="stats-list"><div><span>Aplikasi</span><b>{branding.app_name} V{version}</b></div><div><span>Zona Waktu Operasional</span><b>Asia/Makassar (WITA)</b></div><div><span>Database</span><b>PostgreSQL</b></div><div><span>Backup</span><b>Jalankan melalui skrip server</b></div></div></Panel></div>
}

export default function App(){
 const {branding}=useBranding();
 const [version,setVersion]=useState('—');
 const topologyDirty=useRef(false);
 const [topologyFocus,setTopologyFocus]=useState(false);
 const [topologyTarget,setTopologyTarget]=useState<DiagramNav|null>(null);
 const [topologyTrail,setTopologyTrail]=useState<DiagramNav[]>([]);
 const acceptedPage=useRef<Page>(route());
 const [user,setUser]=useState<User|null>(null),[catalog,setCatalog]=useState<Catalog|null>(null),[page,setPage]=useState<Page>(route()),[loading,setLoading]=useState(true),[menu,setMenu]=useState(false),[globalError,setGlobalError]=useState('');
 function refreshCatalog(){api<Catalog>('/catalog').then(setCatalog).catch(e=>setGlobalError(errMessage(e)))}
 useEffect(()=>{api<{version:string}>('/health').then(r=>setVersion(r.version)).catch(()=>{});api<{user:User,csrf:string}>('/auth/me').then(r=>{setCSRF(r.csrf);setUser(r.user)}).catch(()=>{}).finally(()=>setLoading(false));const change=()=>{const next=route();if((topologyDirty.current||hasDirty())&&next!==acceptedPage.current&&!window.confirm('Ada perubahan belum tersimpan. Tinggalkan halaman?')){window.history.replaceState(null,'','#/'+acceptedPage.current);return;}topologyDirty.current=false;acceptedPage.current=next;setPage(next);setMenu(false);setTopologyFocus(false)};window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change)},[]);
 const {unitTree,unit,unitRevision,unitReady,chooseUnit}=useActiveUnit(user,()=>{
  if((topologyDirty.current||hasDirty())&&!window.confirm('Ada perubahan belum tersimpan. Ganti unit?'))return false;
  topologyDirty.current=false;setCatalog(null);return true;
 },setGlobalError);
 useEffect(()=>{if(user&&unitReady&&unit)refreshCatalog()},[user,unitReady,unitRevision]);
 function navigate(key:Page){if((topologyDirty.current||hasDirty())&&!window.confirm('Ada perubahan belum tersimpan. Tinggalkan halaman?'))return;topologyDirty.current=false;go(key)}
 async function logout(){if((topologyDirty.current||hasDirty())&&!window.confirm('Ada perubahan belum tersimpan. Keluar?'))return;try{await api('/auth/logout',{method:'POST'})}finally{setCSRF('');setUser(null);go('dashboard')}}
 if(loading)return <div className="boot"><Activity size={45}/><Loading/></div>;
 if(!user)return <Login onLogin={setUser}/>;
 if(!unitReady)return <Loading/>;
 if(!unit)return <div className="boot"><Notice type="error">Tidak ada unit aktif yang boleh dibaca. Hubungi admin untuk penugasan akses unit.</Notice><button className="btn secondary" onClick={logout}>Keluar</button></div>;
 function followDiagram(unitId:number,diagramId:number,day:string,hour:number,currentDiagramId:number|null,currentName:string){
  if(!unit)return;
  setTopologyTrail(prev=>[...prev,{unitId:unit.id,diagramId:currentDiagramId,name:currentName,day,hour}]);
  setTopologyTarget({unitId,diagramId,name:'',day,hour});chooseUnit(unitId);
 }
 function returnDiagram(index:number){
  const entry=topologyTrail[index];if(!entry)return;
  setTopologyTarget(entry);setTopologyTrail(prev=>prev.slice(0,index));chooseUnit(entry.unitId);
 }
 const current=navigation.find(n=>n.key===page)||navigation[0];
 const readonly=!canWrite(unit,user.role);
 const effectiveUser:User=readonly?{...user,role:'management'}:user.role==='admin'?user:{...user,role:unit.roles?.includes('verifier')?'verifier':'operator'};
 const unitLineage=(()=>{
  const nodes=flattenUnits(unitTree),byId=new Map(nodes.map(row=>[row.id,row]));
  const names:string[]=[];let parent:UnitNode|undefined=unit;
  while(parent){names.unshift(parent.name);parent=parent.parent_id?byId.get(parent.parent_id):undefined;}
  return names;
 })();
 const rootSelected=isRootOnly(unit);
 const hiddenPages=rootSelected?['input','imports']:readonly?['imports']:[];
 const visibleNavigation=navigation.filter(item=>!hiddenPages.includes(item.key));
 const pageBlocked=hiddenPages.includes(page);

 return <div className={'shell'+(page==='topology'&&topologyFocus?' topology-focus':'')}><aside className={'sidebar '+(menu?'shown':'')}><div className="sidebar-brand"><BrandMark/><div><b>{branding.app_short_name}</b><span>{branding.has_logo||branding.tagline!=='Sistem Kelistrikan Berau'?branding.tagline:'Monitoring System'}</span></div><button className="mobile-close" onClick={()=>setMenu(false)}><X size={22}/></button></div><div className="sidebar-context"><UnitSelector tree={unitTree} value={unit?.id??null} onSelect={id=>{setTopologyTrail([]);setTopologyTarget(null);chooseUnit(id)}}/></div><nav>{visibleNavigation.map((v,i)=>{const Icon=v.icon;const groupStart=i===0||visibleNavigation[i-1].group!==v.group;return <div key={v.key}>{groupStart&&<div className="nav-group">{v.group}</div>}<button className={'nav-link '+(page===v.key?'selected':'')} onClick={()=>navigate(v.key)}><Icon size={19}/><span>{v.label}</span>{page===v.key&&<ChevronRight size={16}/>}</button></div>})}</nav><div className="sidebar-foot"><div className="sidebar-avatar">{user.name.slice(0,2).toUpperCase()}</div><div><b>{user.name}</b><small>{user.role}</small></div><button title="Keluar" onClick={logout}><LogOut size={18}/></button></div></aside>{menu&&<div className="mobile-backdrop" onClick={()=>setMenu(false)}/>}
 <div className={'workspace'+(page==='topology'?' workspace-topology':'')}><header className="topbar"><button className="hamburger" onClick={()=>setMenu(true)}><Menu size={23}/></button><div className="breadcrumb"><span>{unit?.name??"Pilih unit"}</span><ChevronRight size={14}/><strong>{current.label}</strong></div><div className="topbar-right"><span className="tz-chip"><span className="live-dot"/> WITA · Data historis</span><div className="user-avatar">{user.name.slice(0,2).toUpperCase()}</div></div></header><main key={unitRevision} className={page==='topology'?'content content-topology':'content'}><SessionBanner/><div className="unit-active-banner"><strong>{unit?.name??'Unit belum dipilih'}</strong>{readonly&&<span className="tag warning">{viewModeLabel(unit,user.role)}</span>}{user.role==='admin'&&!rootSelected&&<span className="muted small">Bertindak sebagai admin UP3 di {unit?.name}</span>}</div>{pageBlocked&&<Notice>{rootDataHint(unit)} untuk halaman ini.</Notice>}{globalError&&<Notice type="error">{globalError}</Notice>}{catalog&&(!catalog.roles?.['system.load']||!catalog.roles?.['system.capacity'])&&['dashboard','builder','history','analytics','reports'].includes(page)&&<Notice>Parameter utama belum diatur. {user.role==='admin'&&<a href="#/settings" onClick={()=>sessionStorage.setItem('berauload_settings_tab','primary')}>Buka Pengaturan → Parameter utama unit</a>}</Notice>}{page==='dashboard'&&<DashboardHome catalog={catalog||{assets:[],metrics:[]}} user={effectiveUser}
 classic={()=> <DashboardPage catalog={catalog||{assets:[],metrics:[]}} user={user}/>}/>}{page==='builder'&&<DashboardBuilder catalog={catalog||{assets:[],metrics:[]}} user={effectiveUser}/>}{page==='completeness'&&<UnitCompleteness unitId={unit.id} onOpen={(target,day)=>{chooseUnit(target);try{sessionStorage.setItem(unitCacheKey('berauload_day'),day)}catch{}navigate('input')}}/>}{page==='topology'&&<TopologyPage unitLevel={unit.level} unitName={unit.name}
  target={topologyTarget} trail={topologyTrail} unitPath={unitLineage} onFollow={followDiagram} onBack={returnDiagram} isAdmin={user.role==='admin'} metrics={catalog?.metrics??[]} assets={catalog?.assets??[]} onDirtyChange={value=>{topologyDirty.current=value}} focused={topologyFocus} onToggleFocus={()=>setTopologyFocus(value=>!value)}/>} {page==='help'&&<HelpPage version={version}/>}{!pageBlocked&&page==='input'&&<InputPage catalog={catalog||{assets:[],metrics:[]}} user={effectiveUser} unitLevel={unit?.level??'up3'}/>}{page==='substations'&&<SubstationsPage user={effectiveUser} readonly={readonly} level={unit.level}/>} {page==='history'&&<HistoryPage/>}{page==='analytics'&&<AnalyticsPage catalog={catalog||{assets:[],metrics:[]}} user={effectiveUser}/>}{page==='plants'&&<AnalyticsPage catalog={catalog||{assets:[],metrics:[]}} lockedGroup="PEMBANGKIT"/>}{page==='feeders'&&<AnalyticsPage catalog={catalog||{assets:[],metrics:[]}} lockedGroup="FEEDER"/>}{page==='reports'&&<ReportsPage catalog={catalog||{assets:[],metrics:[]}} user={effectiveUser}/>}{page==='export'&&<ExportBuilder catalog={catalog||{assets:[],metrics:[]}} role={effectiveUser.role}/>}{!pageBlocked&&page==='imports'&&<ImportsPage user={user}/ >}{page==='settings'&&<SettingsPage catalog={catalog||{assets:[],metrics:[]}} refreshCatalog={refreshCatalog} user={user} version={version}/>}</main><footer className="footer">{branding.app_name} V{version} <span>•</span> {branding.footer_text} <span>•</span> Asia/Makassar (WITA)</footer></div></div>
}
