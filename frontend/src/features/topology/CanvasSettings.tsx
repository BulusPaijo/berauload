/** Manual page dimensions; layout configuration only, never alters any object or reading. */
import {useEffect,useState} from 'react';
import type {TopologyLayout} from './types';
import {contentBounds,resizeCanvas} from './workspaceState.mjs';
type Props={layout:TopologyLayout;onChange:(next:TopologyLayout)=>void};
export default function CanvasSettings({layout,onChange}:Props){
 const [w,setW]=useState(layout.canvas.w),[h,setH]=useState(layout.canvas.h);
 const [error,setError]=useState('');
 useEffect(()=>{setW(layout.canvas.w);setH(layout.canvas.h);setError('')},[layout.canvas.w,layout.canvas.h]);
 function apply(width:number,height:number){
  const next=resizeCanvas(layout,width,height);
  if(!next){setError('Ukuran 200–20.000 px (grid 10); tidak boleh memotong objek.');return;}
  setError('');onChange(next);
 }
 function fit(){const b=contentBounds(layout);
  apply(Math.min(20000,Math.max(200,Math.ceil((b.maxX+200)/400)*400)),
   Math.min(20000,Math.max(200,Math.ceil((b.maxY+200)/400)*400)));
 }
 return <div className="topo-canvas-settings">
  <div className="topo-property-heading">Ukuran Kanvas</div>
  <div className="topo-properties-grid">
   <label>Lebar (px)<input type="number" min={200} max={20000} step={10} value={w}
    onChange={e=>setW(Number(e.target.value))}/></label>
   <label>Tinggi (px)<input type="number" min={200} max={20000} step={10} value={h}
    onChange={e=>setH(Number(e.target.value))}/></label>
  </div>
  <button type="button" onClick={()=>apply(w,h)}>Terapkan Ukuran</button>
  <button type="button" onClick={fit}>Sesuaikan ke Objek</button>
  <small className="topo-faint">Saat objek mendekati tepi, kanvas bertambah otomatis. Tidak ada objek yang dipindahkan saat kanvas bertambah.</small>
  {error&&<small role="alert" className="topo-input-warning">{error}</small>}
 </div>;
}
