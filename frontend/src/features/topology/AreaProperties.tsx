import type {TopologyArea} from './types';
type Props={area:TopologyArea;onPatch:(patch:Partial<TopologyArea>)=>void;onRemove:()=>void};
export default function AreaProperties({area:a,onPatch,onRemove}:Props){
 return <aside className="topo-properties" aria-label="Properti area visual">
  <h3>Properti Area / Kelompok</h3><span className="topo-editor-id">{a.id} · Hanya visual</span>
  <label>Judul area<input value={a.title} maxLength={100} onChange={e=>onPatch({title:e.target.value})}/></label>
  <div className="topo-properties-grid">
   <label>X<input type="number" min={0} step={10} value={a.x} onChange={e=>onPatch({x:Number(e.target.value)})}/></label>
   <label>Y<input type="number" min={0} step={10} value={a.y} onChange={e=>onPatch({y:Number(e.target.value)})}/></label>
   <label>Lebar<input type="number" min={40} step={10} value={a.w} onChange={e=>onPatch({w:Number(e.target.value)})}/></label>
   <label>Tinggi<input type="number" min={40} step={10} value={a.h} onChange={e=>onPatch({h:Number(e.target.value)})}/></label>
  </div>
  <label>Garis<select value={a.border} onChange={e=>onPatch({border:e.target.value as TopologyArea['border']})}>
   <option value="solid">Solid</option><option value="dashed">Putus-putus</option><option value="dotted">Titik-titik</option>
  </select></label>
  <label>Warna<select value={a.color} onChange={e=>onPatch({color:e.target.value as TopologyArea['color']})}>
   <option value="blue">Biru</option><option value="teal">Teal</option><option value="green">Hijau</option>
   <option value="amber">Kuning</option><option value="red">Merah</option><option value="gray">Abu-abu</option>
  </select></label>
  <label>Isi area · {a.opacity}%<input aria-label="Opasitas isi area" type="range" min={0} max={40} step={5}
   value={a.opacity} onChange={e=>onPatch({opacity:Number(e.target.value)})}/></label>
  <label className="topo-check-row"><input type="checkbox" checked={a.locked}
   onChange={e=>onPatch({locked:e.target.checked})}/> Kunci posisi area</label>
  <p className="topo-faint">Area adalah bingkai visual saja. Garis dan simbol di dalamnya tidak tersambung atau berpindah otomatis.</p>
  <button type="button" className="topo-danger" onClick={onRemove}>Hapus Area</button>
 </aside>;
}
