import {SourceStatusSummary} from '../unit-references/SourceStatus';
/** Single Line Viewer + Stage 3 admin-only configuration editor. */
import {useEffect,useState} from 'react';
import type {FormEvent} from 'react';
import {Activity,AlertCircle,X} from 'lucide-react';
import {isoWita} from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import type {Metric,Asset} from '../../api';
import type {TopologyBox,TopologyDiagram,TopologyHour,TopologySeries,DiagramUnit,TopologySymbol} from './types';
import {topologyApi} from './topologyApi';
import Canvas from './Canvas';
import TimeBar from './TimeBar';
import {hourLabel} from './viewerFormatting.mjs';
import TrendDrawer from './TrendDrawer';
import ViewerToolbar from './ViewerToolbar';
import {contentBounds} from './workspaceState.mjs';
import TopologyEditor from './TopologyEditor';
import './topology.css';

const witaHour=()=>Number(new Intl.DateTimeFormat('en-GB',{
 timeZone:'Asia/Makassar',hour:'2-digit',hourCycle:'h23'}).format(new Date()));
const errorText=(e:unknown)=>e instanceof Error?e.message:String(e);

function useDiagramList(initialId:number|null){
 const [list,setList]=useState<TopologyDiagram[]>([]);
 const [id,setId]=useState<number|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [revision,setRevision]=useState(0);
 useEffect(()=>{
  let alive=true;setLoading(true);
  topologyApi.list().then(rows=>{if(alive){setList(rows);setId(current=>rows.some(r=>r.id===initialId)?initialId:rows.some(r=>r.id===current)?current:rows[0]?.id??null);setError('')}})
   .catch(e=>{if(alive)setError(errorText(e))}).finally(()=>{if(alive)setLoading(false)});
  return()=>{alive=false};
 },[revision]);
 return {list,id,setId,loading,error,revision,refresh:()=>setRevision(n=>n+1)};
}

function useDiagram(id:number|null,revision:number){
 const [diagram,setDiagram]=useState<TopologyDiagram|null>(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{
  let alive=true;setDiagram(null);setError('');
  if(id===null)return;
  setLoading(true);
  topologyApi.one(id).then(row=>{if(alive)setDiagram(row)})
   .catch(e=>{if(alive)setError(errorText(e))}).finally(()=>{if(alive)setLoading(false)});
  return()=>{alive=false};
 },[id,revision]);
 return {diagram,loading,error};
}

function useHour(id:number|null,day:string,hour:number,revision:number){
 const [data,setData]=useState<TopologyHour|null>(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{
  let alive=true;setData(null);setError('');
  if(id===null||!day)return;
  setLoading(true);
  topologyApi.hour(id,day,hour).then(row=>{if(alive)setData(row)})
   .catch(e=>{if(alive)setError(errorText(e))}).finally(()=>{if(alive)setLoading(false)});
  return()=>{alive=false};
 },[id,day,hour,revision]);
 return {data,loading,error};
}


function useDaySeries(id:number|null,day:string,revision:number){
 const [series,setSeries]=useState<TopologySeries|null>(null);
 useEffect(()=>{
  let alive=true;setSeries(null);
  if(id===null||!day)return;
  topologyApi.series(id,day).then(value=>{if(alive)setSeries(value)}).catch(()=>{});
  return()=>{alive=false};
 },[id,day,revision]);
 return series;
}

export type DiagramNav={unitId:number;diagramId:number|null;name:string;day:string;hour:number};
export default function TopologyPage({isAdmin,metrics,assets,onDirtyChange,focused,onToggleFocus,unitLevel,unitName,
 target,trail,unitPath,onFollow,onBack}:{
 isAdmin:boolean;metrics:Metric[];assets:Asset[];onDirtyChange:(dirty:boolean)=>void;focused:boolean;onToggleFocus:()=>void;
 unitLevel:string;unitName:string;target:DiagramNav|null;trail:DiagramNav[];unitPath:string[];
 onFollow:(unitId:number,diagramId:number,day:string,hour:number,currentDiagramId:number|null,currentName:string)=>void;
 onBack:(index:number)=>void}){
 const referenceMetrics=useUnitMetricReferences();
 const usableMetrics=metricsForSelection(referenceMetrics,metrics);
 const names=Object.fromEntries(usableMetrics.map(m=>[m.code,'label' in m ? String(m.label) : m.name]));
 const diagrams=useDiagramList(target?.diagramId??null);
 const [targets,setTargets]=useState<DiagramUnit[]>([]);
 const [browse,setBrowse]=useState<DiagramUnit[]>([]);
 const selected=useDiagram(diagrams.id,diagrams.revision);
 const [day,setDay]=useState(target?.day??isoWita());
 const [hour,setHour]=useState(target?.hour??witaHour());
 const [playing,setPlaying]=useState(false);
 const [zoom,setZoom]=useState(.9);
 const [detail,setDetail]=useState<TopologyBox|null>(null);
 const [editing,setEditing]=useState(false);
 const [creating,setCreating]=useState(false);
 const [newName,setNewName]=useState(''),[newDescription,setNewDescription]=useState('');
 const [createBusy,setCreateBusy]=useState(false),[createError,setCreateError]=useState('');
 useEffect(()=>{
  let alive=true;
  topologyApi.linkTargets().then(rows=>{if(alive)setTargets(rows)}).catch(()=>{if(alive)setTargets([])});
  if(unitLevel==='up3')topologyApi.browse().then(rows=>{if(alive)setBrowse(rows)}).catch(()=>{});
  return()=>{alive=false};
 },[unitLevel]);
 const allowedLinks=new Set(targets.flatMap(unit=>unit.diagrams.map(diagram=>diagram.id)));
 function followSymbol(symbol:TopologySymbol){
  if(!symbol.link||!allowedLinks.has(symbol.link.diagram_id))return;
  onFollow(symbol.link.unit_id,symbol.link.diagram_id,day,hour,diagrams.id,unitName);
 }
 const reading=useHour(selected.diagram?.id??null,day,hour,diagrams.revision);
 const series=useDaySeries(selected.diagram?.id??null,day,diagrams.revision);
 useEffect(()=>{
  if(!playing||diagrams.id===null)return;
  const timer=window.setInterval(()=>setHour(previous=>{
   if(previous>=23){setPlaying(false);return previous}return previous+1;
  }),1800);
  return()=>window.clearInterval(timer);
 },[playing,diagrams.id]);
 function chooseDay(value:string){setDay(value);setPlaying(false);setDetail(null)}
 function chooseDiagram(value:number){diagrams.setId(value);setPlaying(false);setDetail(null)}
 async function createDiagram(e:FormEvent<HTMLFormElement>){
  e.preventDefault();setCreateError('');setCreateBusy(true);
  try{
   const row=await topologyApi.create(newName.trim(),newDescription.trim());
   diagrams.setId(row.id);diagrams.refresh();setCreating(false);setNewName('');setNewDescription('');
  }catch(e){setCreateError(errorText(e))}finally{setCreateBusy(false)}
 }
 function savedDiagram(updated:TopologyDiagram){
  diagrams.setId(updated.id);diagrams.refresh();setEditing(false);
 }
 const error=diagrams.error||selected.error||reading.error;
 function fitCanvas(){
  const width=document.querySelector<HTMLElement>('.topo-main .topo-scroll')?.clientWidth;
  const canvasWidth=selected.diagram?.layout.canvas.w;
  const bounds=selected.diagram?contentBounds(selected.diagram.layout):null;
  if(width&&canvasWidth&&bounds)setZoom(Math.max(.1,Math.min(1.5,Math.floor((width-24)/(Math.max(bounds.maxX,400)+80)*100)/100)));
 }
 useEffect(()=>{if(!focused)return;const key=(event:KeyboardEvent)=>{if(event.key==='Escape')onToggleFocus();};
  window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[focused,onToggleFocus]);
 return <section className={'topology-page'+(editing?' is-editing':'')}>
  <nav className="topo-nav-breadcrumb" aria-label="Jejak diagram">
   <span>{unitPath.join(' > ')}</span>
   {trail.map((entry,index)=><button type="button" key={`${entry.unitId}-${index}`}
    onClick={()=>onBack(index)}>Kembali ke {entry.name}</button>)}
  </nav>
  {unitLevel==='up3'&&<section className="topo-hierarchy"><strong>Diagram ULP dan KP</strong>
   {browse.filter(u=>u.level!=='up3').map(u=><div key={u.unit_id} className="topo-hierarchy-row">
    <span>{u.level.toUpperCase()} · {u.unit_name}</span>
    {u.diagrams.length?u.diagrams.map(d=><button type="button" key={d.id}
     onClick={()=>onFollow(u.unit_id,d.id,day,hour,diagrams.id,unitName)}>{d.name} ↗</button>):
     <small>Belum ada diagram</small>}
   </div>)}
  </section>}
  {!editing&&<ViewerToolbar diagrams={diagrams.list} selectedId={diagrams.id} busy={diagrams.loading}
   zoom={zoom} onZoom={setZoom} onSelect={chooseDiagram} onRefresh={diagrams.refresh} onFit={fitCanvas}
   focused={focused} onToggleFocus={onToggleFocus} isAdmin={isAdmin} hasDiagram={!!selected.diagram}
   onCreate={()=>setCreating(true)} onEdit={()=>{setPlaying(false);setDetail(null);setEditing(true);}}/>}
  {creating&&<form className="topo-create-form" onSubmit={createDiagram}>
    <strong>Buat Diagram Kosong</strong>
    <label>Nama diagram<input value={newName} onChange={e=>setNewName(e.target.value)}
      maxLength={150} minLength={2} required placeholder="Contoh: Sistem Berau — Diagram Kerja"/></label>
    <label>Deskripsi<input value={newDescription} maxLength={500} onChange={e=>setNewDescription(e.target.value)}/></label>
    <button type="submit" disabled={createBusy||newName.trim().length<2}>Buat Diagram</button>
    <button type="button" onClick={()=>{setCreating(false);setCreateError('')}}><X size={15}/> Batal</button>
    {createError&&<span role="alert">{createError}</span>}
   </form>}
  {error&&<div className="topo-error" role="alert"><AlertCircle size={16}/>{error}</div>}
  {editing&&selected.diagram?<TopologyEditor key={`${selected.diagram.id}-${selected.diagram.version}`}
   diagram={selected.diagram} assets={assets} metrics={usableMetrics} hour={reading.data} series={series}
   zoom={zoom} onZoom={setZoom} onExit={()=>setEditing(false)} onSave={savedDiagram} onDirtyChange={onDirtyChange} focused={focused} onToggleFocus={onToggleFocus}/>
  :<div className="topo-main">
   {diagrams.loading||selected.loading?<div className="topo-empty-state">Memuat diagram...</div>:
    !selected.diagram?<div className="topo-empty-state"><Activity size={42}/>
     <h3>Belum ada diagram Single Line</h3>
     <p>Diagram tidak dibuat otomatis agar sambungan jaringan tidak keliru.
      {isAdmin?' Admin dapat menyusun simbol, garis manual, dan kotak melalui Mode Edit.':''}</p>
    </div>:<><div className="topo-canvas-meta"><div><strong>{selected.diagram.name}</strong>
     <span>{selected.diagram.description||'Koneksi diagram merupakan konfigurasi, bukan hasil verifikasi otomatis'}</span></div>
     <span>Rev {selected.diagram.version} · {selected.diagram.layout.symbols.length} simbol · {selected.diagram.layout.boxes.length} kotak · {selected.diagram.layout.areas?.length||0} area</span>
    </div><Canvas layout={selected.diagram.layout} hour={reading.data} series={series} zoom={zoom} names={names} onBoxClick={setDetail} allowedLinks={allowedLinks} onLink={followSymbol}/></>}
  </div>}
  <SourceStatusSummary status={reading.data?.source_status}/>
  <TimeBar day={day} hour={hour} playing={playing&&diagrams.id!==null}
   status={reading.data?.day_status??null} busy={reading.loading}
   setDay={chooseDay} setHour={setHour} setPlaying={setPlaying}/>
  <div className="topo-disclaimer topo-sr-only">Data jam {hourLabel(hour)} WITA · Nilai kosong ditampilkan “—”.
   Warna kondisi hanya berasal dari Engineering Rules aktif yang dipilih pada kotak.
   Simbol pemutus bersifat netral dan tidak dapat dioperasikan.</div>
  {!editing&&detail&&selected.diagram&&<TrendDrawer box={detail} diagramId={selected.diagram.id}
   day={day} names={names} onClose={()=>setDetail(null)}/>} 
 </section>;
}
