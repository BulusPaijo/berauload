/** Dashboard utama memakai konfigurasi dashboard yang sama dengan Builder. */
import {useEffect,useMemo,useState} from 'react';
import {LayoutDashboard,Settings2} from 'lucide-react';
import {api,isoWita,type Catalog,type User} from '../../api';
import type {DashLayout,LayoutList,PaneContext} from './types';
import PanelCard from './PanelCard';
import type {UnitItem} from '../units/UnitManager';
import './dashboard-builder.css';

const errorMessage=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function DashboardHome({catalog,user,classic}:{
  catalog:Catalog;user:User;classic:()=>React.ReactNode;
}){
  const now=isoWita();
  const [year,setYear]=useState(Number(now.slice(0,4)));
  const [month,setMonth]=useState(Number(now.slice(5,7)));
  const [classicView,setClassicView]=useState(false);
  const [layout,setLayout]=useState<DashLayout|null>(null);
  const [units,setUnits]=useState<UnitItem[]>([]);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnits).catch(()=>{});},[]);
  useEffect(()=>{
    let mounted=true;
    api<LayoutList>('/dashboard-builder').then(data=>{
      if(!mounted)return;
      const id=data.effective_default_id;
      setLayout(data.items.find(item=>item.id===id)||null);
    }).catch(e=>{if(mounted)setError(errorMessage(e))})
      .finally(()=>{if(mounted)setLoading(false)});
    return()=>{mounted=false};
  },[user.id]);
  const start=`${year}-${String(month).padStart(2,'0')}-01`;
  const end=year===Number(now.slice(0,4))&&month===Number(now.slice(5,7))?
    now:new Date(Date.UTC(year,month,0)).toISOString().slice(0,10);
  const ctx=useMemo<PaneContext>(()=>({start,end,granularity:'day',catalog,units}),[start,end,catalog,units]);
  return <div className="page-space dashboard-builder">
    <div className="page-top"><div><div className="eyebrow">RINGKASAN OPERASIONAL</div>
      <h2>Dashboard Beban Sistem</h2><p>{layout?.name||'Monitoring Kelistrikan Berau'}</p></div>
      <div className="dash-toolbar-actions">
        <button className="btn secondary sm" onClick={()=>setClassicView(v=>!v)}>
          {classicView?'Dashboard Kustom':'Tampilan Klasik'}</button>
        <button className="btn primary sm" onClick={()=>{window.location.hash='/builder'}}>
          <Settings2 size={15}/> Kelola Dashboard</button>
      </div></div>
    {classicView?classic():<>
      <div className="dash-toolbar panel"><div className="dash-toolbar-left">
        <label>Bulan<select value={month} onChange={e=>setMonth(Number(e.target.value))}>
          {Array.from({length:12},(_,i)=><option key={i} value={i+1}>{String(i+1).padStart(2,'0')}</option>)}</select></label>
        <label>Tahun<select value={year} onChange={e=>setYear(Number(e.target.value))}>
          {Array.from({length:26},(_,i)=><option key={i} value={2015+i}>{2015+i}</option>)}</select></label>
      </div><span className="dash-tip">Grafik mengambil data historis yang tersedia, bukan SCADA real-time.</span></div>
      {error&&<div className="notice error" role="alert">{error}</div>}
      {loading&&<div className="panel dash-empty">Memuat dashboard default...</div>}
      {!loading&&layout&&<div className="dash-grid">{layout.panels.map(panel=><PanelCard key={panel.id}
        panel={panel} ctx={ctx} editing={false} onEdit={()=>{}} onRemove={()=>{}}
        onMove={()=>{}} onResize={()=>{}} onDragStart={()=>{}} onDragEnd={()=>{}} onDrop={()=>{}}/>)}</div>}
      {!loading&&!layout&&!error&&<div className="panel dash-empty"><LayoutDashboard size={24}/>
        Dashboard default belum tersedia. Admin dapat mengaturnya melalui Dashboard Builder.</div>}
    </>}
  </div>;
}
