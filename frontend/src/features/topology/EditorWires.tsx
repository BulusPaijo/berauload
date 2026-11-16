/** Select wire and drag vertices using native SVG pointer capture. */
import {useRef} from 'react';
import type {PointerEvent as ReactPointerEvent} from 'react';
import type {TopologyWire} from './types';
import {normalPoint} from './stage4State.mjs';
import type {TopologyLayout} from './types';
const COLORS={'20kv':'#43b8fa',unspecified:'#7d9fb0'} as const;
type Props={layout:TopologyLayout;selectedId:string|null;active:boolean;
 onSelect:(id:string)=>void;onVertex:(id:string,index:number,x:number,y:number)=>void;
 onSelectedVertex:(index:number)=>void};
const pointOf=(e:ReactPointerEvent<SVGElement>,layout:TopologyLayout):[number,number]=>{
 const svg=e.currentTarget.ownerSVGElement;
 if(!svg)return [0,0];
 const r=svg.getBoundingClientRect();
 return normalPoint(layout,(e.clientX-r.left)*layout.canvas.w/r.width,
  (e.clientY-r.top)*layout.canvas.h/r.height);
};
export default function EditorWires(p:Props){
 const drag=useRef<{id:string;index:number;pointerId:number}|null>(null);
 return <g className="topo-wire-layer">
  {p.layout.wires.map(w=><g key={w.id}>
   <polyline points={w.points.map(pt=>pt.join(',')).join(' ')} fill="none"
    stroke={COLORS[w.level]} strokeWidth={p.selectedId===w.id?5:4} strokeLinecap="round" strokeLinejoin="round"/>
   {p.active&&<polyline points={w.points.map(pt=>pt.join(',')).join(' ')} fill="none"
    stroke="transparent" strokeWidth={18} strokeLinecap="round" strokeLinejoin="round"
    className="topo-wire-hit" onPointerDown={e=>{e.stopPropagation();p.onSelect(w.id)}}/>}
   {p.active&&p.selectedId===w.id&&w.points.map(([x,y],index)=><circle key={index}
    cx={x} cy={y} r={8} fill="#0c4255" stroke="#a2f9ff" strokeWidth={2}
    className="topo-vertex-hit" aria-label={`Geser titik ${index+1} garis ${w.id}`}
    onPointerDown={e=>{e.stopPropagation();e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);
     drag.current={id:w.id,index,pointerId:e.pointerId};p.onSelectedVertex(index)}}
    onPointerUp={e=>{e.stopPropagation();if(!drag.current||drag.current.pointerId!==e.pointerId)return;
     const [px,py]=pointOf(e,p.layout);p.onVertex(w.id,index,px,py);drag.current=null}}
    onPointerCancel={()=>{drag.current=null}}/>)}
  </g>)}
 </g>;
}
