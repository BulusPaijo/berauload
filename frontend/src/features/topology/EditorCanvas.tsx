/** SVG-only editor, no electrical status or inferred connectivity. */
import {useRef,useState} from 'react';
import type {PointerEvent as ReactPointerEvent,DragEvent as ReactDragEvent} from 'react';
import type {TopologyHour,TopologyLayout,TopologyBox,TopologySeries,SymbolType} from './types';
import type {EditorTool} from './Palette';
import SymbolGlyph from './symbols';
import ParamBox from './ParamBox';
import AreaFrame from './AreaFrame';
import EditorWires from './EditorWires';
import {boxHeight,place} from './editorState.mjs';
import {normalPoint,SYMBOL_TYPES} from './stage4State.mjs';
import {patchArea} from './workspaceState.mjs';
export type Selection={kind:'box'|'symbol'|'wire'|'area';id:string}|null;
type ItemType='box'|'symbol'|'area';
type Drag={id:string;type:ItemType;clientX:number;clientY:number;startX:number;startY:number;x:number;y:number};
type Resize={id:string;clientX:number;clientY:number;w:number;h:number};
type Props={layout:TopologyLayout;hour:TopologyHour|null;series:TopologySeries|null;
 zoom:number;names:Record<string,string>;selection:Selection;tool:EditorTool;
 wirePoints:[number,number][];onSelect:(selected:Selection)=>void;
 onMove:(id:string,type:ItemType,x:number,y:number)=>void;
 onResizeArea:(id:string,w:number,h:number)=>void;
 onWirePoint:(id:string,index:number,x:number,y:number)=>void;onSelectedVertex:(index:number)=>void;
 onCanvasPoint:(x:number,y:number)=>void;onPlaceSymbol:(type:SymbolType,x:number,y:number)=>void;
 onPlaceArea:(x:number,y:number)=>void};
const clientToPoint=(e:{clientX:number;clientY:number},svg:SVGSVGElement,layout:TopologyLayout)=>{
 const r=svg.getBoundingClientRect();
 return normalPoint(layout,(e.clientX-r.left)*layout.canvas.w/r.width,
  (e.clientY-r.top)*layout.canvas.h/r.height);
};
export default function EditorCanvas(p:Props){
 const dragRef=useRef<Drag|null>(null),resizeRef=useRef<Resize|null>(null);
 const [preview,setPreview]=useState<Drag|null>(null);
 const [sizePreview,setSizePreview]=useState<{id:string;w:number;h:number}|null>(null);
 const [cursor,setCursor]=useState<[number,number]|null>(null);
 const {layout}=p;
 const onDown=(e:ReactPointerEvent<SVGRectElement>,type:ItemType,id:string,x:number,y:number)=>{
  if(e.button!==0||p.tool.kind!=='select')return;
  const item=type==='box'?layout.boxes.find(b=>b.id===id):
   type==='area'?layout.areas?.find(a=>a.id===id):null;
  p.onSelect({kind:type,id});
  if(item?.locked)return;
  e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);
  dragRef.current={id,type,clientX:e.clientX,clientY:e.clientY,startX:x,startY:y,x,y};
  setPreview(dragRef.current);
 };
 const onDrag=(e:ReactPointerEvent<SVGRectElement>)=>{
  const d=dragRef.current;if(!d)return;
  const rect=e.currentTarget.ownerSVGElement?.getBoundingClientRect();if(!rect)return;
  const dx=(e.clientX-d.clientX)*layout.canvas.w/rect.width;
  const dy=(e.clientY-d.clientY)*layout.canvas.h/rect.height;
  const moved=d.type==='area'?patchArea(layout,d.id,{x:d.startX+dx,y:d.startY+dy}):
   place(layout,d.id,d.type,d.startX+dx,d.startY+dy);
  const item=(d.type==='box'?moved.boxes:d.type==='symbol'?moved.symbols:moved.areas||[]).find(v=>v.id===d.id);
  if(!item)return;
  dragRef.current={...d,x:item.x,y:item.y};setPreview(dragRef.current);
 };
 const onEnd=()=>{
  const d=dragRef.current;dragRef.current=null;setPreview(null);
  if(d&&(d.x!==d.startX||d.y!==d.startY))p.onMove(d.id,d.type,d.x,d.y);
 };
 const pose=(id:string,x:number,y:number)=>preview?.id===id?{x:preview.x,y:preview.y}:{x,y};
 const resizeDown=(e:ReactPointerEvent<SVGRectElement>,id:string,w:number,h:number)=>{
  if(e.button!==0)return;e.stopPropagation();e.preventDefault();
  e.currentTarget.setPointerCapture(e.pointerId);
  resizeRef.current={id,clientX:e.clientX,clientY:e.clientY,w,h};
 };
 const resizeMove=(e:ReactPointerEvent<SVGRectElement>)=>{
  const d=resizeRef.current;if(!d)return;
  const rect=e.currentTarget.ownerSVGElement?.getBoundingClientRect();if(!rect)return;
  const grid=layout.canvas.grid;
  const w=Math.max(40,Math.round((d.w+(e.clientX-d.clientX)*layout.canvas.w/rect.width)/grid)*grid);
  const h=Math.max(40,Math.round((d.h+(e.clientY-d.clientY)*layout.canvas.h/rect.height)/grid)*grid);
  setSizePreview({id:d.id,w,h});
 };
 const resizeEnd=()=>{
  const d=resizeRef.current;resizeRef.current=null;
  if(d&&sizePreview&&(sizePreview.w!==d.w||sizePreview.h!==d.h))
   p.onResizeArea(d.id,sizePreview.w,sizePreview.h);
  setSizePreview(null);
 };
 const anchors=new Map(layout.symbols.map(s=>{
  const pos=pose(s.id,s.x,s.y);return [s.id,{x:pos.x+s.w/2,y:pos.y+s.h/2}];
 }));
 const clickCanvas=(e:ReactPointerEvent<SVGRectElement>)=>{
  if(e.button!==0)return;
  const svg=e.currentTarget.ownerSVGElement;if(!svg)return;
  const [x,y]=clientToPoint(e,svg,layout);
  if(p.tool.kind==='wire')p.onCanvasPoint(x,y);
  else if(p.tool.kind==='area')p.onPlaceArea(x,y);
  else if(p.tool.kind==='symbol'&&p.tool.symbolType)p.onPlaceSymbol(p.tool.symbolType,x,y);
  else p.onSelect(null);
 };
 const dropSymbol=(e:ReactDragEvent<SVGSVGElement>)=>{
  e.preventDefault();const type=e.dataTransfer.getData('application/x-berauload-symbol');
  if(!SYMBOL_TYPES.includes(type as SymbolType))return;
  const [x,y]=clientToPoint(e,e.currentTarget,layout);p.onPlaceSymbol(type as SymbolType,x,y);
 };
 return <div className="topo-scroll" aria-label="Kanvas editor single line">
  <svg className="topo-svg" width={layout.canvas.w*p.zoom} height={layout.canvas.h*p.zoom}
   viewBox={`0 0 ${layout.canvas.w} ${layout.canvas.h}`} role="group"
   onDragOver={e=>e.preventDefault()} onDrop={dropSymbol}>
   <defs><pattern id="topo-editor-grid" width={layout.canvas.grid} height={layout.canvas.grid} patternUnits="userSpaceOnUse">
    <path d="M 10 0 L 0 0 0 10" stroke="#173c53" strokeWidth=".6" fill="none"/>
   </pattern></defs>
   <rect width="100%" height="100%" fill="#091929"/>
   <rect width="100%" height="100%" fill="url(#topo-editor-grid)"/>
   {(layout.areas||[]).map(a=>{
    const pos=pose(a.id,a.x,a.y),sz=sizePreview?.id===a.id?sizePreview:a;
    return <g key={a.id}>
     <AreaFrame area={{...a,...pos,w:sz.w,h:sz.h}} selected={p.selection?.kind==='area'&&p.selection.id===a.id}/>
     <rect x={pos.x} y={pos.y} width={sz.w} height={sz.h} fill="none" stroke="transparent"
      strokeWidth={13} pointerEvents="stroke" className={a.locked?'topo-locked-hit':'topo-drag-hit'}
      onPointerDown={e=>onDown(e,'area',a.id,a.x,a.y)}
      onPointerMove={onDrag} onPointerUp={onEnd} onPointerCancel={onEnd}/>
     {p.selection?.kind==='area'&&p.selection.id===a.id&&!a.locked&&
      <rect x={pos.x+sz.w-9} y={pos.y+sz.h-9} width={18} height={18} fill="#67e6e8"
       stroke="#092133" strokeWidth={2} className="topo-area-resize"
       onPointerDown={e=>resizeDown(e,a.id,a.w,a.h)} onPointerMove={resizeMove}
       onPointerUp={resizeEnd} onPointerCancel={resizeEnd}/>}
    </g>;
   })}
   <EditorWires layout={layout} selectedId={p.selection?.kind==='wire'?p.selection.id:null}
    active={p.tool.kind==='select'} onSelect={id=>p.onSelect({kind:'wire',id})}
    onVertex={p.onWirePoint} onSelectedVertex={p.onSelectedVertex}/>
   {layout.symbols.map(s=>{
    const pos=pose(s.id,s.x,s.y);
    return <g key={s.id}><SymbolGlyph symbol={{...s,...pos}}/>
     <rect x={pos.x} y={pos.y} width={s.w} height={s.h} fill="transparent"
      stroke={p.selection?.id===s.id?'#68ebee':'transparent'} strokeDasharray="5 5"
      className="topo-drag-hit" onPointerDown={e=>onDown(e,'symbol',s.id,s.x,s.y)}
      onPointerMove={onDrag} onPointerUp={onEnd} onPointerCancel={onEnd}/>
    </g>;
   })}
   {layout.boxes.map((b:TopologyBox)=>{
    const pos=pose(b.id,b.x,b.y),h=boxHeight(b);
    const anchor=b.anchor_symbol_id?anchors.get(b.anchor_symbol_id):null;
    return <g key={b.id}>
     {b.leader&&anchor&&<line x1={pos.x+b.w/2} y1={pos.y+h/2} x2={anchor.x} y2={anchor.y}
       stroke="#9cbbcd" strokeDasharray="6 6" strokeWidth={1.6}/>}
     <foreignObject x={pos.x} y={pos.y} width={b.w} height={h}>
      <div className="topo-foreign topo-no-actions"><ParamBox box={b} data={p.hour} series={p.series}
       names={p.names} onDetails={()=>p.onSelect({kind:'box',id:b.id})}/></div>
     </foreignObject>
     <rect x={pos.x} y={pos.y} width={b.w} height={h} rx={8} fill="transparent"
      stroke={p.selection?.id===b.id?'#67e6e8':'transparent'} strokeWidth={2} strokeDasharray="7 4"
      className={b.locked?'topo-locked-hit':'topo-drag-hit'} aria-label={`Pilih dan geser ${b.title}`}
      onPointerDown={e=>onDown(e,'box',b.id,b.x,b.y)}
      onPointerMove={onDrag} onPointerUp={onEnd} onPointerCancel={onEnd}/>
    </g>;
   })}
   {p.tool.kind!=='select'&&<rect x={0} y={0} width={layout.canvas.w} height={layout.canvas.h}
    fill="transparent" className="topo-placement-surface" onPointerDown={clickCanvas}
    onPointerMove={e=>{
     const svg=e.currentTarget.ownerSVGElement;
     if(svg)setCursor(clientToPoint(e,svg,layout));
    }} onPointerLeave={()=>setCursor(null)}/>}
   {p.tool.kind==='wire'&&p.wirePoints.length>0&&<g pointerEvents="none">
    <polyline points={[...p.wirePoints,...(cursor?[cursor]:[])].map(pt=>pt.join(',')).join(' ')}
     stroke="#5cebe5" strokeWidth={3} strokeDasharray="8 5" fill="none"/>
    {p.wirePoints.map(([x,y],i)=><circle key={i} cx={x} cy={y} r={5} fill="#72ebee"/>)}
   </g>}
  </svg>
 </div>;
}
