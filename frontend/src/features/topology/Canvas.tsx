/** SVG-only fixed viewer: no mutable electrical or diagram controls. */
import type {TopologyBox,TopologyHour,TopologyLayout,TopologySeries,TopologySymbol} from './types';
import SymbolGlyph from './symbols';
import ParamBox, {boxHeight} from './ParamBox';
import AreaFrame from './AreaFrame';

const wireColor={"20kv":"#43b8fa",unspecified:'#7d9fb0'} as const;
type Props={layout:TopologyLayout;hour:TopologyHour|null;series?:TopologySeries|null;zoom:number;names:Record<string,string>;
 onBoxClick:(box:TopologyBox)=>void;onLink?:(symbol:TopologySymbol)=>void;allowedLinks?:Set<number>};

export default function Canvas({layout,hour,series,zoom,names,onBoxClick,onLink,allowedLinks}:Props){
 const {canvas,symbols,wires,boxes}=layout;
 const anchors=new Map(symbols.map(s=>[s.id,{x:s.x+s.w/2,y:s.y+s.h/2}]));
 const anyContent=symbols.length+wires.length+boxes.length+(layout.areas?.length||0)>0;
 return <div className="topo-scroll" aria-label="Kanvas diagram Single Line, hanya lihat">
  <svg className="topo-svg" width={canvas.w*zoom} height={canvas.h*zoom}
   viewBox={`0 0 ${canvas.w} ${canvas.h}`} role="group"
   aria-label={`Diagram berisi ${symbols.length} simbol, ${wires.length} garis dan ${boxes.length} kotak parameter dan ${layout.areas?.length||0} area visual`}>
   <defs><pattern id="topo-grid" width={canvas.grid} height={canvas.grid} patternUnits="userSpaceOnUse">
     <path d={`M ${canvas.grid} 0 L 0 0 0 ${canvas.grid}`} stroke="#173c53" strokeWidth={0.6} fill="none"/>
   </pattern></defs>
   <rect width={canvas.w} height={canvas.h} fill="#091929"/>
   <rect width={canvas.w} height={canvas.h} fill="url(#topo-grid)"/>
   {(layout.areas||[]).map(a=><AreaFrame key={a.id} area={a}/>)}
   {wires.map(w=><polyline key={w.id} points={w.points.map(p=>p.join(',')).join(' ')}
    fill="none" stroke={wireColor[w.level]??wireColor.unspecified}
    strokeWidth={4} strokeLinecap="round" strokeLinejoin="round"/>)}
   {symbols.map(s=>{
    const linked=s.link&&allowedLinks?.has(s.link.diagram_id);
    return <g key={s.id} className={linked?'topo-linked-symbol':''} tabIndex={linked?0:undefined}
     role={linked?'button':undefined} aria-label={linked?`Buka diagram unit bawah dari ${s.label}`:undefined}
     onClick={linked?()=>onLink?.(s):undefined}
     onKeyDown={linked?e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onLink?.(s)}}:undefined}>
     <SymbolGlyph symbol={s}/>
     {linked&&<g transform={`translate(${s.x+s.w-4},${s.y+4})`}>
      <circle r={13} fill="#055e82" stroke="#fff" strokeWidth={2}/>
      <text textAnchor="middle" dominantBaseline="central" fontSize={17} fill="white">↗</text>
     </g>}
    </g>;
   })}
   {boxes.map(b=>{
    const h=boxHeight(b),y=Math.max(0,Math.min(b.y,canvas.h-h));
    const x=Math.max(0,Math.min(b.x,canvas.w-b.w));
    const anchor=b.anchor_symbol_id?anchors.get(b.anchor_symbol_id):undefined;
    return <g key={b.id}>
      {b.leader&&anchor&&<line x1={x+b.w/2} y1={y+h/2} x2={anchor.x} y2={anchor.y}
       stroke="#93b6ca" strokeWidth={1.7} strokeDasharray="7 5"/>}
      <foreignObject x={x} y={y} width={b.w} height={h}>
       <div className="topo-foreign"><ParamBox box={b} data={hour} series={series} names={names} onDetails={onBoxClick}/></div>
      </foreignObject>
    </g>;
   })}
   {!anyContent&&<g className="topo-canvas-empty" textAnchor="middle">
     <text x={canvas.w/2} y={canvas.h/2-20} fontSize={28} fontWeight={750} fill="#c3deed">Diagram belum mempunyai objek</text>
     <text x={canvas.w/2} y={canvas.h/2+20} fontSize={16} fill="#85a7ba">Koneksi jaringan tidak dibuat otomatis. Admin dapat menyusun diagram pada Mode Edit.</text>
   </g>}
  </svg>
 </div>;
}
