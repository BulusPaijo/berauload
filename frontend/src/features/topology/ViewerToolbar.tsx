/** Compact, read-only topology navigation; no SCADA controls. */
import {Layers3,Maximize2,Minimize2,Minus,Plus,RefreshCw,Pencil,PlusSquare,Info} from 'lucide-react';
import type {TopologyDiagram} from './types';
type Props={diagrams:TopologyDiagram[];selectedId:number|null;busy:boolean;zoom:number;
 onSelect:(id:number)=>void;onRefresh:()=>void;onZoom:(zoom:number)=>void;onFit:()=>void;
 focused:boolean;onToggleFocus:()=>void;isAdmin:boolean;hasDiagram:boolean;
 onCreate:()=>void;onEdit:()=>void};
export default function ViewerToolbar(p:Props){
 return <header className="topo-compact-toolbar" aria-label="Navigasi topologi">
  <div className="topo-compact-title"><Layers3 size={19}/><strong>Topologi Single Line</strong>
   <span className="topo-info-tooltip" title="Pembacaan historis per jam WITA. Jalur listrik digambar manual. Pemutus tidak dapat dioperasikan.">
    <Info size={15}/><span className="topo-sr-only">Diagram pemantauan data historis, bukan SCADA</span></span>
  </div>
  <label className="topo-compact-diagram"><span className="topo-sr-only">Diagram</span>
   <select value={p.selectedId??''} disabled={p.busy||!p.diagrams.length}
    onChange={e=>p.onSelect(Number(e.target.value))} aria-label="Pilih diagram">
    {!p.diagrams.length?<option value="">Belum ada diagram</option>:
     p.diagrams.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
   </select>
  </label>
  <div className="topo-compact-actions">
   <button type="button" title="Segarkan diagram" onClick={p.onRefresh}><RefreshCw size={15}/><span className="topo-action-label">Muat ulang</span></button>
   <button type="button" title="Sesuaikan zoom dengan isi diagram" onClick={p.onFit}>Fit</button>
   <div className="topo-zoom" aria-label="Perbesaran kanvas">
    <button type="button" aria-label="Perkecil kanvas" disabled={p.zoom<=.1}
     onClick={()=>p.onZoom(Math.max(.1,+(p.zoom-.1).toFixed(2)))}><Minus size={15}/></button>
    <span>{Math.round(p.zoom*100)}%</span>
    <button type="button" aria-label="Perbesar kanvas" disabled={p.zoom>=1.5}
     onClick={()=>p.onZoom(Math.min(1.5,+(p.zoom+.1).toFixed(2)))}><Plus size={15}/></button>
   </div>
   {p.isAdmin&&<><button type="button" onClick={p.onCreate} title="Diagram kosong baru"><PlusSquare size={15}/><span className="topo-action-label">Baru</span></button>
    {p.hasDiagram&&<button type="button" className="topo-primary" onClick={p.onEdit}><Pencil size={15}/><span className="topo-action-label">Edit</span></button>}</>}
   <button type="button" onClick={p.onToggleFocus} aria-pressed={p.focused} title="Tampilkan/sembunyikan sidebar">
    {p.focused?<Minimize2 size={15}/>:<Maximize2 size={15}/>}<span className="topo-action-label">{p.focused?'Menu':'Fokus'}</span></button>
  </div>
 </header>;
}
