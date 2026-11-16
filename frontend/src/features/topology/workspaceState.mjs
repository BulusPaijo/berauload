/** Pure layout expansion and visual areas; no electrical connectivity inferred. */
import {clone,nearest,newId,boxHeight} from './editorState.mjs';
export const MAX_CANVAS=20000;
const GRID=10,STEP=400;
const snap=(n,grid)=>nearest(Math.max(0,Number.isFinite(n)?n:0),grid);
const cap=(value)=>Math.min(MAX_CANVAS,value);
const grow=(now,required,grid)=>cap(Math.max(now,Math.ceil(required/STEP)*STEP,grid));
export function expandForRect(layout,x,y,w,h,padding=120){
 const next=clone(layout),grid=next.canvas.grid;
 next.canvas.w=grow(next.canvas.w,snap(x+w+padding,grid),grid);
 next.canvas.h=grow(next.canvas.h,snap(y+h+padding,grid),grid);
 return next;
}
export function expandForPoint(layout,x,y,padding=120){
 return expandForRect(layout,x,y,0,0,padding);
}
export function contentBounds(layout){
 const ends=[...layout.symbols.map(s=>[s.x+s.w,s.y+s.h]),
  ...layout.boxes.map(b=>[b.x+b.w,b.y+boxHeight(b)]),
  ...(layout.areas||[]).map(a=>[a.x+a.w,a.y+a.h]),
  ...layout.wires.flatMap(w=>w.points)];
 const xs=[...layout.symbols.map(s=>s.x),...layout.boxes.map(b=>b.x),
  ...(layout.areas||[]).map(a=>a.x),...layout.wires.flatMap(w=>w.points.map(p=>p[0]))];
 const ys=[...layout.symbols.map(s=>s.y),...layout.boxes.map(b=>b.y),
  ...(layout.areas||[]).map(a=>a.y),...layout.wires.flatMap(w=>w.points.map(p=>p[1]))];
 return {minX:Math.max(0,Math.min(...xs,0)),minY:Math.max(0,Math.min(...ys,0)),
  maxX:ends.length?Math.max(...ends.map(e=>e[0])):0,
  maxY:ends.length?Math.max(...ends.map(e=>e[1])):0};
}
export function resizeCanvas(layout,width,height){
 const next=clone(layout),grid=next.canvas.grid,bounds=contentBounds(next);
 const minW=Math.max(200,Math.ceil(bounds.maxX/grid)*grid);
 const minH=Math.max(200,Math.ceil(bounds.maxY/grid)*grid);
 if(!Number.isFinite(width)||!Number.isFinite(height))return null;
 const w=snap(width,grid),h=snap(height,grid);
 if(w<minW||h<minH||w>MAX_CANVAS||h>MAX_CANVAS)return null;
 next.canvas={...next.canvas,w,h};return next;
}
export const AREA_BORDERS=['solid','dashed','dotted'];
export const AREA_COLORS=['teal','blue','amber','green','red','gray'];
const clean=text=>String(text).replace(/[<>{}`;\u0000-\u001f]/g,' ').replace(/--/g,'–').slice(0,100).trim();
export function addArea(layout,x=30,y=30){
 if((layout.areas||[]).length>=100)return null;
 const next=expandForRect(layout,x,y,340,220);
 if(x+340>MAX_CANVAS||y+220>MAX_CANVAS)return null;
 next.areas=next.areas||[];
 next.areas.push({id:newId(next,'area'),x:snap(x,next.canvas.grid),y:snap(y,next.canvas.grid),
  w:340,h:220,title:'Kelompok Peralatan',border:'dashed',color:'blue',opacity:10,locked:false});
 return next;
}
export function patchArea(layout,id,patch){
 const next=clone(layout),area=(next.areas||[]).find(a=>a.id===id);
 if(!area)return next;
 if(Object.hasOwn(patch,'title'))area.title=clean(patch.title)||'Area';
 if(AREA_BORDERS.includes(patch.border))area.border=patch.border;
 if(AREA_COLORS.includes(patch.color))area.color=patch.color;
 if(Number.isInteger(patch.opacity)&&patch.opacity>=0&&patch.opacity<=40&&patch.opacity%5===0)area.opacity=patch.opacity;
 if(typeof patch.locked==='boolean')area.locked=patch.locked;
 if(area.locked&&!Object.hasOwn(patch,'locked'))return next;
 for(const field of ['x','y','w','h']){
  if(!Object.hasOwn(patch,field)||!Number.isFinite(patch[field]))continue;
  area[field]=snap(Math.max(field==='w'||field==='h'?40:0,patch[field]),next.canvas.grid);
 }
 const grown=expandForRect(next,area.x,area.y,area.w,area.h);
 area.x=Math.min(area.x,grown.canvas.w-area.w);area.y=Math.min(area.y,grown.canvas.h-area.h);
 return grown;
}
export function removeArea(layout,id){
 const next=clone(layout);next.areas=(next.areas||[]).filter(a=>a.id!==id);return next;
}
