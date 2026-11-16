/** Pure visual-topology operations. Never infer connections or store readings. */
import {clone,nearest,newId,boxHeight} from './editorState.mjs';
const TYPES=['generator','incoming','busbar','breaker','transformer','feeder','load','capacitor'];
const clamp=(n,lo,hi)=>Math.max(lo,Math.min(hi,n));
export const SYMBOL_TYPES=TYPES;
export const BOX_TYPES=['metric','summary','ranking','legend','text'];
export const LEVELS=['unspecified','20kv'];
const snap=(value,limit,grid)=>nearest(clamp(value,0,limit),grid);
const safeLabel=(value)=>String(value||'').replace(/[<>{}`;\u0000-\u001f]/g,' ').replace(/--/g,'–').slice(0,120).trim();
export function addSymbol(layout,type,x,y){
 if(!TYPES.includes(type)||layout.symbols.length>=200)return null;
 const next=clone(layout),{grid,w,h}=next.canvas;
 const size=type==='busbar'?{w:180,h:40}:{w:120,h:70};
 next.symbols.push({id:newId(next,'symbol'),type,x:snap(x,w-size.w,grid),
  y:snap(y,h-size.h,grid),...size,asset_code:null,label:`${type[0].toUpperCase()}${type.slice(1)}`,
  rotation:0});
 return next;
}
export function patchSymbol(layout,id,patch){
 const next=clone(layout),symbol=next.symbols.find(s=>s.id===id);
 if(!symbol)return next;
 if(Object.hasOwn(patch,'label'))symbol.label=safeLabel(patch.label);
 if(Object.hasOwn(patch,'asset_code'))symbol.asset_code=patch.asset_code;
 if(Object.hasOwn(patch,'rotation')&&[0,90,180,270].includes(patch.rotation))symbol.rotation=patch.rotation;
 if(Object.hasOwn(patch,'type')&&TYPES.includes(patch.type))symbol.type=patch.type;
 if(Object.hasOwn(patch,'link')){
  if(patch.link&&Number.isInteger(patch.link.unit_id)&&Number.isInteger(patch.link.diagram_id))
   symbol.link={unit_id:patch.link.unit_id,diagram_id:patch.link.diagram_id};
  else delete symbol.link;
 }
 const {grid,w,h}=next.canvas;
 if(Object.hasOwn(patch,'w')&&symbol.type==='busbar'&&Number.isFinite(patch.w)){
  symbol.w=snap(Math.round(patch.w),Math.min(w-symbol.x,1200),grid);
  symbol.w=Math.max(40,Math.min(symbol.w,w-symbol.x));
 }
 if(Object.hasOwn(patch,'x'))symbol.x=snap(patch.x,w-symbol.w,grid);
 if(Object.hasOwn(patch,'y'))symbol.y=snap(patch.y,h-symbol.h,grid);
 return next;
}
export function removeSymbol(layout,id){
 const next=clone(layout);
 next.symbols=next.symbols.filter(s=>s.id!==id);
 for(const box of next.boxes){if(box.anchor_symbol_id===id){box.anchor_symbol_id=null;box.leader=false;}}
 // Drawing paths are authored independently; never imply that wires were attached.
 return next;
}
export function normalPoint(layout,x,y){
 const {grid,w,h}=layout.canvas;
 return [snap(x,w,grid),snap(y,h,grid)];
}
export function validPolyline(points){
 return points.length>=2&&points.length<=32&&points.every((p,i)=>i===0||p[0]!==points[i-1][0]||p[1]!==points[i-1][1]);
}
export function addWire(layout,points,level='unspecified'){
 if(layout.wires.length>=300||!LEVELS.includes(level)||!Array.isArray(points))return null;
 const clean=points.map(p=>normalPoint(layout,p[0],p[1]));
 if(!validPolyline(clean))return null;
 const next=clone(layout);next.wires.push({id:newId(next,'wire'),points:clean,level});
 return next;
}
export function removeWire(layout,id){
 const next=clone(layout);next.wires=next.wires.filter(w=>w.id!==id);return next;
}
export function changeWireLevel(layout,id,level){
 const next=clone(layout),wire=next.wires.find(w=>w.id===id);
 if(wire&&LEVELS.includes(level))wire.level=level;
 return next;
}
export function moveWirePoint(layout,id,index,x,y){
 const next=clone(layout),wire=next.wires.find(w=>w.id===id);
 if(!wire||index<0||index>=wire.points.length)return next;
 const point=normalPoint(next,x,y),points=wire.points.map((p,i)=>i===index?point:p);
 if(validPolyline(points))wire.points=points;
 return next;
}
export function addWireVertex(layout,id,index){
 const next=clone(layout),wire=next.wires.find(w=>w.id===id);
 if(!wire||wire.points.length>=32||index<0||index>=wire.points.length-1)return next;
 const a=wire.points[index],b=wire.points[index+1];
 const mid=normalPoint(next,(a[0]+b[0])/2,(a[1]+b[1])/2);
 if(mid[0]===a[0]&&mid[1]===a[1]||mid[0]===b[0]&&mid[1]===b[1])return next;
 wire.points.splice(index+1,0,mid);return next;
}
export function removeWireVertex(layout,id,index){
 const next=clone(layout),wire=next.wires.find(w=>w.id===id);
 if(!wire||wire.points.length<=2||index<0||index>=wire.points.length)return next;
 wire.points.splice(index,1);
 if(!validPolyline(wire.points))return clone(layout);
 return next;
}
export function addDisplayBox(layout,kind,metricCode=null){
 if(!BOX_TYPES.includes(kind)||layout.boxes.length>=100)return null;
 if(['metric','summary','ranking'].includes(kind)&&!metricCode)return null;
 const next=clone(layout),index=next.boxes.length,{grid,w,h}=next.canvas;
 const metricCodes=metricCode?[metricCode]:[];
 const box={id:newId(next,'box'),kind,x:0,y:0,w:240,
  title:{metric:'Parameter',summary:'Ringkasan Pembacaan',ranking:'Peringkat Parameter',
   legend:'Legenda Diagram',text:'Keterangan'}[kind],asset_code:null,metric_codes:metricCodes,
  decimals:2,show_unit:true,leader:false,sparkline:false,locked:false,
  rule_id:null,anchor_symbol_id:null};
 const x=nearest(30+(index%5)*280,grid),y=nearest(30+Math.floor(index/5)*170,grid);
 next.canvas.w=Math.min(20000,Math.max(next.canvas.w,Math.ceil((x+box.w+120)/400)*400));
 next.canvas.h=Math.min(20000,Math.max(next.canvas.h,Math.ceil((y+boxHeight(box)+120)/400)*400));
 box.x=snap(x,w-box.w,grid);box.y=snap(y,Math.max(0,h-boxHeight(box)),grid);
 next.boxes.push(box);return next;
}
