/** Stage 4: admin SVG builder. Drafts contain only validated configuration. */
import {useEffect,useState} from 'react';
import {Check,RotateCcw,Save,Undo2,Redo2,X,AlertTriangle,Maximize2,Minimize2} from 'lucide-react';
import type {Asset,Metric} from '../../api';
import type {TopologyBox,TopologyDiagram,TopologyHour,TopologyRule,TopologyRevision,
 TopologySeries,SymbolType,BoxKind,TopologySymbol,WireLevel,DiagramUnit} from './types';
import {topologyApi} from './topologyApi';
import EditorCanvas from './EditorCanvas';
import type {Selection} from './EditorCanvas';
import PropertiesPanel from './PropertiesPanel';
import SymbolProperties from './SymbolProperties';
import WireProperties from './WireProperties';
import AreaProperties from './AreaProperties';
import CanvasSettings from './CanvasSettings';
import Palette from './Palette';
import type {EditorTool} from './Palette';
import {useTopologyDraft} from './useTopologyDraft';
import {addMetricBox,applySameKind,assetDraft,duplicateBox,place,rebindBox,
 removeBox,updateBox,validEditorMetric} from './editorState.mjs';
import {addSymbol,removeSymbol,patchSymbol,addWire,removeWire,changeWireLevel,
 moveWirePoint,addWireVertex,removeWireVertex,addDisplayBox} from './stage4State.mjs';
import {contentBounds,expandForRect,expandForPoint,addArea,patchArea,removeArea} from './workspaceState.mjs';
type Props={diagram:TopologyDiagram;assets:Asset[];metrics:Metric[];hour:TopologyHour|null;
 series:TopologySeries|null;zoom:number;onZoom:(value:number)=>void;onExit:()=>void;onSave:(updated:TopologyDiagram)=>void;
 onDirtyChange:(dirty:boolean)=>void;focused:boolean;onToggleFocus:()=>void};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);
export default function TopologyEditor(p:Props){
 const history=useTopologyDraft(p.diagram),draft=history.draft,layout=draft.layout;
 const [selection,setSelection]=useState<Selection>(null);
 const [tool,setTool]=useState<EditorTool>({kind:'select'});
 const [wirePoints,setWirePoints]=useState<[number,number][]>([]);
 const [wireLevel,setWireLevel]=useState<WireLevel>('unspecified');
 const [vertexIndex,setVertexIndex]=useState(0);
 const [assetCode,setAssetCode]=useState(''),[metricCode,setMetricCode]=useState('');
 const [rules,setRules]=useState<TopologyRule[]>([]);
 const [targets,setTargets]=useState<DiagramUnit[]>([]);
 const [revisions,setRevisions]=useState<TopologyRevision[]>([]);
 const [saving,setSaving]=useState(false),[error,setError]=useState(''),[info,setInfo]=useState('');
 const box=selection?.kind==='box'?layout.boxes.find(b=>b.id===selection.id)??null:null;
 const symbol=selection?.kind==='symbol'?layout.symbols.find(s=>s.id===selection.id)??null:null;
 const wire=selection?.kind==='wire'?layout.wires.find(w=>w.id===selection.id)??null:null;
 const area=selection?.kind==='area'?layout.areas?.find(a=>a.id===selection.id)??null:null;
 const available=p.metrics.filter(m=>validEditorMetric(m,assetCode||null,p.assets));
 const names=Object.fromEntries(p.metrics.map(m=>[m.code,m.name]));
 const dirty=history.dirty||wirePoints.length>0;
 useEffect(()=>{topologyApi.rules().then(setRules).catch(()=>{});
  topologyApi.revisions(p.diagram.id).then(setRevisions).catch(()=>{});
  topologyApi.linkTargets().then(setTargets).catch(()=>{});},[p.diagram.id]);
 useEffect(()=>{p.onDirtyChange(dirty);return()=>p.onDirtyChange(false)},[dirty,p.onDirtyChange]);
 useEffect(()=>{
  const listener=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue='';}};
  window.addEventListener('beforeunload',listener);
  return()=>window.removeEventListener('beforeunload',listener);
 },[dirty]);
 const editLayout=(operation:(layout:typeof draft.layout)=>typeof draft.layout)=>
  history.apply(d=>({...d,layout:operation(d.layout)}));
 const patchBox=(patch:Partial<TopologyBox>)=>{if(box)editLayout(l=>updateBox(l,box.id,patch));};
 const move=(id:string,type:'box'|'symbol'|'area',x:number,y:number)=>
  editLayout(l=>type==='area'?patchArea(l,id,{x,y}):place(l,id,type,x,y));
 const rebind=(code:string|null)=>{
  if(!box)return;
  const permitted=p.metrics.filter(m=>validEditorMetric(m,code,p.assets)).map(m=>m.code);
  editLayout(l=>rebindBox(l,box.id,code,permitted));
 };
 const addBox=(kind:BoxKind)=>{
  const metric=available.find(m=>m.code===(metricCode||available[0]?.code));
  if(['metric','summary','ranking'].includes(kind)&&!metric){setError('Pilih parameter aktif.');return;}
  const next=kind==='metric'?addMetricBox(layout,{asset_code:assetCode||null,
   metric_code:metric?.code??'',title:metric?.name.slice(0,120)}):addDisplayBox(layout,kind,['summary','ranking'].includes(kind)?metric?.code:null);
  if(!next){setError('Kotak tidak dapat ditambahkan. Periksa batas 100 kotak.');return;}
  if(kind!=='metric'&&assetCode)next.boxes[next.boxes.length-1].asset_code=assetCode;
  editLayout(()=>next);setSelection({kind:'box',id:next.boxes[next.boxes.length-1].id});
  setTool({kind:'select'});setError('');
 };
 const addSymbolAt=(type:SymbolType,x:number,y:number)=>{
  const next=addSymbol(expandForRect(layout,x,y,type==='busbar'?180:120,70),type,x,y);
  if(!next){setError('Tidak dapat menambah simbol: batas 200 tercapai.');return;}
  editLayout(()=>next);setSelection({kind:'symbol',id:next.symbols[next.symbols.length-1].id});setError('');
 };
 const drawPoint=(x:number,y:number)=>{
  if(x>layout.canvas.w-120||y>layout.canvas.h-120)editLayout(l=>expandForPoint(l,x,y));
  if(wirePoints.length>=32){setError('Maksimal 32 titik per garis. Selesaikan garis.');return;}
  if(wirePoints.some((pt,i)=>i===wirePoints.length-1&&pt[0]===x&&pt[1]===y))return;
  setWirePoints(points=>[...points,[x,y]]);setError('');
 };
 const finishWire=()=>{
  const next=addWire(layout,wirePoints,wireLevel);
  if(!next){setError('Minimal 2 titik berbeda, maksimal 32 titik / 300 garis.');return;}
  editLayout(()=>next);setSelection({kind:'wire',id:next.wires[next.wires.length-1].id});
  setWirePoints([]);setTool({kind:'select'});setVertexIndex(0);setError('');
 };
 const addAreaAt=(x:number,y:number)=>{
  const next=addArea(layout,x,y);
  if(!next){setError('Maksimal 100 area atau batas kanvas tercapai.');return;}
  editLayout(()=>next);setSelection({kind:'area',id:next.areas![next.areas!.length-1].id});
  setTool({kind:'select'});setError('');
 };
 const chooseTool=(next:EditorTool)=>{
  if(wirePoints.length&&next.kind!=='wire'&&!window.confirm('Batalkan garis yang belum diselesaikan?'))return;
  if(next.kind!=='wire')setWirePoints([]);
  setTool(next);setSelection(null);
 };
 const draftAssets=()=>{
  const result=assetDraft(layout,p.assets.filter(a=>a.active));
  if(result.added)editLayout(()=>result.layout);
  setInfo(`${result.added} simbol ditambahkan TANPA garis, ${result.skipped} dilewati.`);
 };
 const removeSelected=()=>{
  if(!selection||!window.confirm('Hapus objek dari draf? Data pengukuran tidak berubah.'))return;
  editLayout(l=>selection.kind==='box'?removeBox(l,selection.id):
   selection.kind==='symbol'?removeSymbol(l,selection.id):
   selection.kind==='area'?removeArea(l,selection.id):removeWire(l,selection.id));
  setSelection(null);
 };
 const duplicate=()=>{
  if(!box)return;
  const next=duplicateBox(layout,box.id);
  if(!next){setError('Batas 100 kotak tercapai.');return;}
  editLayout(()=>next);setSelection({kind:'box',id:next.boxes[next.boxes.length-1].id});
 };
 const applyKind=()=>{
  if(!box)return;
  if(!window.confirm('Salin bila kunci peran cocok; bila tidak ada kunci, nama+satuan harus sama persis?'))return;
  const result=applySameKind(layout,box.id,p.assets,p.metrics);
  if(result.added)editLayout(()=>result.layout);
  setInfo(`${result.added} kotak dibuat; ${result.skipped} dilewati.`);
 };
 const fitEditor=()=>{
  const width=document.querySelector<HTMLElement>('.topo-editor-canvas .topo-scroll')?.clientWidth;
  const bounds=contentBounds(layout);
  if(width)p.onZoom(Math.max(.1,Math.min(1.5,Math.floor((width-24)/
   (Math.max(bounds.maxX,400)+80)*100)/100)));
 };
 const leave=()=>{if(dirty&&!window.confirm('Buang perubahan draf yang belum disimpan?'))return;p.onExit();};
 const reset=()=>{
  if(!dirty||window.confirm('Reset seluruh perubahan ke versi tersimpan?')){
   history.reset();setWirePoints([]);setSelection(null);setTool({kind:'select'});
  }
 };
 async function save(){
  if(wirePoints.length){setError('Selesaikan atau batalkan garis yang sedang digambar.');return;}
  if(layout.boxes.some(b=>['metric','summary','ranking'].includes(b.kind)&&!b.metric_codes.length)){
   setError('Kotak Parameter/Ringkasan/Peringkat wajib memiliki 1–6 parameter.');return;
  }
  setSaving(true);setError('');
  try{const updated=await topologyApi.save(p.diagram.id,p.diagram.version,draft.name,draft.description,layout);
   p.onDirtyChange(false);p.onSave(updated);
  }catch(e){const msg=message(e);setError(msg.includes('409')||msg.includes('diubah pengguna lain')?
   'Diagram sudah diubah pengguna lain, muat ulang.':msg);
  }finally{setSaving(false)}
 }
 async function restore(version:number){
  if(!window.confirm(`Pulihkan revisi ${version} sebagai versi baru? Draf akan dibuang.`))return;
  setSaving(true);setError('');
  try{const updated=await topologyApi.restore(p.diagram.id,version,p.diagram.version);
   p.onDirtyChange(false);p.onSave(updated);
  }catch(e){setError(message(e))}finally{setSaving(false)}
 }
 return <section className="topo-editor" aria-label="Mode Edit Topologi">
  <header className="topo-editor-header"><div><strong>Mode Edit · {p.diagram.name}</strong>
   <span>Revisi {p.diagram.version} · Draf lokal · Tidak menyimpan pembacaan listrik</span></div>
   <div className="topo-editor-actions">
    <button type="button" aria-label="Perkecil diagram" disabled={p.zoom<=.1}
     onClick={()=>p.onZoom(Math.max(.1,+(p.zoom-.1).toFixed(2)))}>−</button>
    <span className="topo-editor-zoom">{Math.round(p.zoom*100)}%</span>
    <button type="button" onClick={fitEditor} title="Sesuaikan isi diagram dengan lebar layar">Fit</button>
    <button type="button" aria-label="Perbesar diagram" disabled={p.zoom>=1.5}
     onClick={()=>p.onZoom(Math.min(1.5,+(p.zoom+.1).toFixed(2)))}>+</button>
    <button type="button" onClick={p.onToggleFocus} aria-pressed={p.focused}>
     {p.focused?<Minimize2 size={15}/>:<Maximize2 size={15}/>} {p.focused?'Tampilkan Menu':'Layar Fokus'}</button>
    <button type="button" disabled={!history.canUndo&&!wirePoints.length||saving} onClick={()=>
     wirePoints.length?setWirePoints(points=>points.slice(0,-1)):history.undo()}><Undo2 size={15}/> Urungkan</button>
    <button type="button" disabled={!history.canRedo||saving||wirePoints.length>0} onClick={history.redo}><Redo2 size={15}/> Ulangi</button>
    <button type="button" disabled={!dirty||saving} onClick={reset}><RotateCcw size={15}/> Reset</button>
    <button type="button" disabled={saving} onClick={leave}><X size={15}/> Batal</button>
    <button type="button" className="topo-primary" disabled={!history.dirty||saving||wirePoints.length>0}
     onClick={save}><Save size={15}/>{saving?'Menyimpan...':'Simpan Perubahan'}</button>
   </div>
  </header>
  {error&&<div className="topo-error" role="alert"><AlertTriangle size={16}/>{error}</div>}
  {info&&<div className="topo-info" role="status"><Check size={15}/>{info}</div>}
  <div className="topo-editor-layout">
   <Palette tool={tool} onTool={chooseTool} onAddBox={addBox} canAddBox={available.length>0}
    assets={p.assets} metrics={available} assetCode={assetCode}
    metricCode={available.some(m=>m.code===metricCode)?metricCode:available[0]?.code??''}
    onAssetCode={code=>{setAssetCode(code);setMetricCode('')}} onMetricCode={setMetricCode}
    onAssetDraft={draftAssets} name={draft.name} description={draft.description}
    onName={name=>history.apply(d=>({...d,name}))} onDescription={description=>history.apply(d=>({...d,description}))}
    revisions={revisions} activeVersion={p.diagram.version} onRestore={restore} saving={saving}
    canvasSettings={<CanvasSettings layout={layout} onChange={next=>editLayout(()=>next)}/>}/>
   <div className="topo-editor-canvas"><div className="topo-editor-subtitle">
    <span>Grid 10 px · Zoom {Math.round(p.zoom*100)}% · Kanvas {layout.canvas.w} × {layout.canvas.h} · Koneksi manual</span>
    <span>{layout.symbols.length}/200 simbol · {layout.wires.length}/300 garis · {layout.boxes.length}/100 kotak · {layout.areas?.length||0}/100 area</span>
   </div>
   {tool.kind==='wire'&&<div className="topo-wire-toolbar">
    <label>Level visual <select value={wireLevel} onChange={e=>setWireLevel(e.target.value as WireLevel)}>
     <option value="unspecified">Belum ditentukan</option><option value="20kv">20 kV</option>
    </select></label>
    <span>{wirePoints.length} titik · Klik kanvas untuk menambah titik</span>
    <button type="button" disabled={wirePoints.length<2} onClick={finishWire}>Selesaikan Garis</button>
    <button type="button" disabled={!wirePoints.length} onClick={()=>setWirePoints([])}>Batalkan Garis</button>
   </div>}
   <EditorCanvas layout={layout} hour={p.hour} series={p.series} zoom={p.zoom} names={names}
    selection={selection} tool={tool} wirePoints={wirePoints} onSelect={setSelection}
    onMove={move} onWirePoint={(id,i,x,y)=>editLayout(l=>moveWirePoint(l,id,i,x,y))}
    onSelectedVertex={setVertexIndex} onCanvasPoint={drawPoint} onPlaceSymbol={addSymbolAt}
    onPlaceArea={addAreaAt} onResizeArea={(id,w,h)=>editLayout(l=>patchArea(l,id,{w,h}))}/>
   </div>
   {area?<AreaProperties area={area} onPatch={patch=>editLayout(l=>patchArea(l,area.id,patch))}
    onRemove={removeSelected}/>:symbol?<SymbolProperties symbol={symbol} assets={p.assets} targets={targets}
    onPatch={(patch:Partial<TopologySymbol>)=>editLayout(l=>patchSymbol(l,symbol.id,patch))}
    onRemove={removeSelected}/>:
    wire?<WireProperties wire={wire} selectedVertex={Math.min(vertexIndex,wire.points.length-1)}
     onSelectVertex={setVertexIndex} onLevel={level=>editLayout(l=>changeWireLevel(l,wire.id,level))}
     onMoveVertex={(i,x,y)=>editLayout(l=>moveWirePoint(l,wire.id,i,x,y))}
     onAddVertex={segment=>editLayout(l=>addWireVertex(l,wire.id,segment))}
     onRemoveVertex={i=>{editLayout(l=>removeWireVertex(l,wire.id,i));setVertexIndex(0)}}
     onRemove={removeSelected}/>:
    <PropertiesPanel box={box} layout={layout} assets={p.assets} metrics={p.metrics}
     rules={rules} onPatch={patchBox} onRebind={rebind}
     onMove={(x,y)=>{if(box)move(box.id,'box',x,y)}}
     onDuplicate={duplicate} onDelete={removeSelected} onApplyKind={applyKind}/>}
  </div>
 </section>;
}
