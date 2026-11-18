import {useState} from 'react';
import type {CalcRule} from './types';
import {dragCodes,orderedCodes} from './helpers.mjs';

type Props={rules:CalcRule[];admin:boolean;active?:number|null;onPick:(rule:CalcRule)=>void;onOrder:(codes:string[])=>Promise<void>|void};
/** 9d-5: category order like the kolom-hitung list — number, ⋮⋮ drag handle, small ↑↓. */
export default function CategoryOrder({rules,admin,active,onPick,onOrder}:Props){
 const [drag,setDrag]=useState<string|null>(null),[over,setOver]=useState<string|null>(null);
 const rows=[...rules].sort((a,b)=>a.display_order-b.display_order||a.id-b.id);
 const drop=(to:string)=>{if(drag&&drag!==to)void onOrder(dragCodes(rows,drag,to));setDrag(null);setOver(null);};
 return <ol className="cat-order">{rows.map((item,i)=><li key={item.id}
   className={'cat-row'+(active===item.id?' active':'')+(over===item.code&&drag!==item.code?' over':'')+(drag===item.code?' dragging':'')}
   draggable={admin} onDragStart={e=>{setDrag(item.code);e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',item.code)}}
   onDragOver={e=>{if(!drag)return;e.preventDefault();setOver(item.code)}} onDragLeave={()=>setOver(o=>o===item.code?null:o)}
   onDrop={e=>{e.preventDefault();drop(item.code)}} onDragEnd={()=>{setDrag(null);setOver(null)}}>
   <span className="cat-no">{i+1}</span>
   {admin&&<span className="cat-grip" aria-hidden="true" title="Seret untuk mengubah urutan">⋮⋮</span>}
   <button className="cat-main" onClick={()=>onPick(item)}><i style={{background:item.color}}/><span><strong>{item.name}</strong><code>{item.expression}</code></span><small>{item.gardu_count} gardu</small></button>
   {admin&&<span className="cat-arrows"><button aria-label={`Naikkan ${item.name}`} title="Naik" disabled={i===0} onClick={()=>void onOrder(orderedCodes(rows,item.code,-1))}>↑</button>
    <button aria-label={`Turunkan ${item.name}`} title="Turun" disabled={i===rows.length-1} onClick={()=>void onOrder(orderedCodes(rows,item.code,1))}>↓</button></span>}
  </li>)}</ol>;
}
