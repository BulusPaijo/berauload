/** Pure editor operations. Configuration only; never handles electrical values. */
export const EMPTY_LAYOUT={canvas:{w:1600,h:900,grid:10},symbols:[],wires:[],boxes:[]};
export const clone=value=>JSON.parse(JSON.stringify(value));
export const nearest=(value,grid)=>Math.round(value/grid)*grid;
function growToFit(next,x,y,w,h){
 const step=400;
 next.canvas.w=Math.min(20000,Math.max(next.canvas.w,Math.ceil((x+w+120)/step)*step));
 next.canvas.h=Math.min(20000,Math.max(next.canvas.h,Math.ceil((y+h+120)/step)*step));
 return next;
}
export const boxHeight=box=>box.kind==='text'?90:box.kind==='legend'?125:
  70+Math.max(1,Math.min(box.metric_codes.length,6))*27+(box.sparkline?64:0)+(box.kind==='summary'?20:0);
const clamp=(x,low,high)=>Math.max(low,Math.min(high,x));
export function place(layout,id,type,x,y){
 const result=clone(layout),items=type==='symbol'?result.symbols:result.boxes;
 const item=items.find(row=>row.id===id);
 if(!item||item.locked)return result;
 const h=type==='symbol'?item.h:boxHeight(item);
 // Grow, never shrink, when dragging near an edge; old object coordinates stay fixed.
 const grow=(old,needed)=>Math.min(20000,Math.max(old,Math.ceil(needed/400)*400));
 if(Number.isFinite(x)&&x>=0&&x<=result.canvas.w)
  result.canvas.w=grow(result.canvas.w,x+item.w+120);
 if(Number.isFinite(y)&&y>=0&&y<=result.canvas.h)
  result.canvas.h=grow(result.canvas.h,y+h+120);
 item.x=clamp(nearest(x,result.canvas.grid),0,result.canvas.w-item.w);
 item.y=clamp(nearest(y,result.canvas.grid),0,Math.max(0,result.canvas.h-h));
 item.x=nearest(item.x,result.canvas.grid);
 item.y=nearest(item.y,result.canvas.grid);
 return result;
}
export function updateBox(layout,id,patch){
 const next=clone(layout),item=next.boxes.find(b=>b.id===id);
 if(!item)return next;
 Object.assign(item,patch);
 if(Object.hasOwn(patch,'w')){
  item.w=nearest(clamp(item.w,10,next.canvas.w),next.canvas.grid);
  item.x=nearest(clamp(item.x,0,next.canvas.w-item.w),next.canvas.grid);
 }
 if(Object.hasOwn(patch,'metric_codes')){
  item.y=nearest(clamp(item.y,0,Math.max(0,next.canvas.h-boxHeight(item))),next.canvas.grid);
 }
 return next;
}
export function newId(layout,prefix){
 const existing=new Set([...layout.symbols,...layout.wires,...layout.boxes,...(layout.areas||[])].map(item=>item.id));
 let index=1;while(existing.has(`${prefix}-${index}`))index++;
 return `${prefix}-${index}`;
}
export function addMetricBox(layout,{asset_code=null,metric_code,title='Kotak Parameter'}){
 if(!metric_code||layout.boxes.length>=100)return null;
 const next=clone(layout),grid=next.canvas.grid;
 const index=next.boxes.length;
 const x=nearest(30+(index%5)*270,grid),y=nearest(30+Math.floor(index/5)*160,grid);
 growToFit(next,x,y,220,190);
 const box={id:newId(next,'box'),kind:'metric',x:Math.min(x,next.canvas.w-220),
  y:0,w:220,title,asset_code,metric_codes:[metric_code],
  decimals:2,show_unit:true,leader:false,sparkline:true,locked:false,
  rule_id:null,anchor_symbol_id:null};
 box.y=nearest(Math.min(y,Math.max(0,next.canvas.h-boxHeight(box))),grid);
 next.boxes.push(box);
 return next;
}
export function duplicateBox(layout,id){
 if(layout.boxes.length>=100)return null;
 const next=clone(layout),item=next.boxes.find(b=>b.id===id);
 if(!item)return null;
 const copy=clone(item),grid=next.canvas.grid;
 copy.id=newId(next,'box');copy.x=nearest(Math.min(item.x+30,next.canvas.w-item.w),grid);
 copy.y=nearest(Math.min(item.y+30,Math.max(0,next.canvas.h-boxHeight(item))),grid);
 next.boxes.push(copy);return next;
}
export function removeBox(layout,id){
 const next=clone(layout);next.boxes=next.boxes.filter(b=>b.id!==id);return next;
}
const ASSET_TYPES={pembangkit:'generator',feeder:'feeder',penyulang:'feeder',incoming:'incoming',
 trafo:'transformer',transformator:'transformer'};
export function assetDraft(layout,assets){
 const next=clone(layout),existing=new Set(next.symbols.map(s=>s.asset_code));
 const candidates=assets.filter(a=>a.active&&!existing.has(a.code));
 const eligible=candidates.filter(a=>ASSET_TYPES[a.kind?.toLowerCase()]);
 let added=0;
 for(const a of eligible){
  if(next.symbols.length>=200)break;
  const index=next.symbols.length,x=30+(index%7)*220,y=30+Math.floor(index/7)*125;
  if(y+65>next.canvas.h)break;
  next.symbols.push({id:newId(next,'symbol'),type:ASSET_TYPES[a.kind.toLowerCase()],
   x,y:nearest(y,next.canvas.grid),w:140,h:60,asset_code:a.code,
   label:a.name.slice(0,120).replace(/[<>{}`;]/g,' ').replace(/--/g,'–').trim()||a.code,
   rotation:0});added++;
 }
 return {layout:next,added,skipped:candidates.length-added};
}
export function validEditorMetric(metric,assetCode,assets){
 if(!metric?.active||metric.code==='daya_mampu_sistem_kw')return false;
 if(assetCode===null)return true;
 const asset=assets.find(a=>a.code===assetCode&&a.active);
 return Boolean(asset&&metric.asset_id===asset.id);
}
export function rebindBox(layout,id,assetCode,allowedCodes){
 const next=clone(layout),box=next.boxes.find(b=>b.id===id);
 if(!box)return next;
 box.asset_code=assetCode;
 box.metric_codes=box.metric_codes.filter(code=>allowedCodes.includes(code));
 box.rule_id=null;
 return next;
}
/** Repeat a box only where every target has an exact, unambiguous name+unit match. */
export function applySameKind(layout,sourceId,assets,metrics){
 const source=layout.boxes.find(b=>b.id===sourceId),owner=assets.find(a=>a.code===source?.asset_code);
 if(!source||!owner)return {layout,added:0,skipped:0};
 const next=clone(layout);
 const targets=assets.filter(a=>a.active&&a.kind===owner.kind&&a.unit_id===owner.unit_id&&a.id!==owner.id);
 let added=0,skipped=0;
 for(const target of targets){
  if(next.boxes.length>=100||next.boxes.some(b=>b.asset_code===target.code)){skipped++;continue;}
  const codes=[];
  for(const code of source.metric_codes){
   const original=metrics.find(m=>m.code===code);
   const matching=metrics.filter(m=>m.active&&m.code!=='daya_mampu_sistem_kw'&&
    m.asset_id===target.id&&(original?.role_key
      ?m.role_key===original.role_key
      :m.name===original?.name&&m.unit===original?.unit));
   if(matching.length!==1)break;
   codes.push(matching[0].code);
  }
  if(codes.length!==source.metric_codes.length||!codes.length){skipped++;continue;}
  const cleanTitle=target.name.slice(0,120).replace(/[<>{}`;]/g,' ').replace(/--/g,'–').trim()||target.code;
  const draft=addMetricBox(next,{asset_code:target.code,metric_code:codes[0],title:cleanTitle});
  if(!draft){skipped++;continue;}
  const item=draft.boxes[draft.boxes.length-1];
  item.metric_codes=codes;item.decimals=source.decimals;item.show_unit=source.show_unit;
  item.sparkline=source.sparkline;item.w=source.w;item.rule_id=null;item.leader=false;
  item.y=nearest(Math.min(item.y,Math.max(0,next.canvas.h-boxHeight(item))),next.canvas.grid);
  next.boxes=draft.boxes;added++;
 }
 return {layout:next,added,skipped};
}
