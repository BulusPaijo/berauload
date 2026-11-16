import type {TopologyWire,WireLevel} from './types';
type Props={wire:TopologyWire;selectedVertex:number;onSelectVertex:(index:number)=>void;
 onLevel:(level:WireLevel)=>void;onMoveVertex:(index:number,x:number,y:number)=>void;
 onAddVertex:(segment:number)=>void;onRemoveVertex:(index:number)=>void;onRemove:()=>void};
export default function WireProperties(p:Props){
 const {wire:w}=p,point=w.points[p.selectedVertex]??w.points[0];
 return <aside className="topo-properties" aria-label="Properti garis">
  <h3>Properti Garis</h3><span className="topo-editor-id">{w.id}</span>
  <label>Label visual jalur<select value={w.level}
   onChange={e=>p.onLevel(e.target.value as WireLevel)}>
   <option value="unspecified">Belum ditentukan</option>
   <option value="20kv">20 kV (label visual saja)</option>
  </select></label>
  <label>Titik garis<select value={p.selectedVertex} onChange={e=>p.onSelectVertex(Number(e.target.value))}>
   {w.points.map((pt,index)=><option key={index} value={index}>Titik {index+1}: {pt.join(', ')}</option>)}
  </select></label>
  <div className="topo-properties-grid">
   <label>X<input type="number" step={10} min={0} value={point[0]}
    onChange={e=>p.onMoveVertex(p.selectedVertex,Number(e.target.value),point[1])}/></label>
   <label>Y<input type="number" step={10} min={0} value={point[1]}
    onChange={e=>p.onMoveVertex(p.selectedVertex,point[0],Number(e.target.value))}/></label>
  </div>
  <div className="topo-editor-actions stack">
   <button type="button" disabled={w.points.length>=32}
    onClick={()=>p.onAddVertex(Math.min(p.selectedVertex,w.points.length-2))}>Tambah titik di segmen</button>
   <button type="button" disabled={w.points.length<=2}
    onClick={()=>p.onRemoveVertex(p.selectedVertex)}>Hapus titik terpilih</button>
   <button type="button" className="topo-danger" onClick={p.onRemove}>Hapus Garis</button>
  </div>
  <p className="topo-faint">Garis dibuat manual sebagai gambar. Tidak menyimpulkan kontinuitas listrik, aliran daya, atau kondisi tegangan.</p>
 </aside>;
}
