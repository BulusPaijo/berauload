import {useEffect,useRef,useState} from 'react';
import {api} from '../../api';
import type {Page,Substation} from './types';

type Props={value:Substation|null;onPick:(s:Substation)=>void;allowed:number[]};
/** Search by gardu number or name (server-side, works for thousands of gardu). */
export default function GarduPicker({value,onPick,allowed}:Props){
 const [q,setQ]=useState(''),[items,setItems]=useState<Substation[]>([]),[open,setOpen]=useState(false),[busy,setBusy]=useState(false),[active,setActive]=useState(0);
 const timer=useRef<number>(0);
 useEffect(()=>{if(!open)return;window.clearTimeout(timer.current);
  timer.current=window.setTimeout(()=>{setBusy(true);api<Page<Substation>>('/substations/master?'+new URLSearchParams({q,page_size:'30',active:'true'}))
   .then(r=>{setItems(r.items.filter(x=>allowed.includes(x.unit_id)));setActive(0)}).catch(()=>setItems([])).finally(()=>setBusy(false))},q?250:0);
  return()=>window.clearTimeout(timer.current);},[q,open,allowed.join(',')]);
 const pick=(s:Substation)=>{onPick(s);setQ('');setOpen(false)};
 return <div className="mf-pick">
  {value&&!open?<button className="mf-picked" onClick={()=>setOpen(true)} aria-label="Ganti gardu"><b>{value.code}</b><span>{value.name}</span><em>Ganti</em></button>
  :<input autoFocus={!!value} type="search" inputMode="search" placeholder="Ketik nomor atau nama gardu" value={q} aria-label="Cari gardu"
    aria-expanded={open} aria-controls="mf-pick-list" onFocus={()=>setOpen(true)} onChange={e=>{setQ(e.target.value);setOpen(true)}}
    onKeyDown={e=>{if(e.key==='ArrowDown'){e.preventDefault();setActive(a=>Math.min(a+1,items.length-1))}else if(e.key==='ArrowUp'){e.preventDefault();setActive(a=>Math.max(a-1,0))}
     else if(e.key==='Enter'&&items[active]){e.preventDefault();pick(items[active])}else if(e.key==='Escape'){setOpen(false)}}}/>}
  {open&&<ul id="mf-pick-list" className="mf-pick-list" role="listbox">
   {items.map((s,i)=><li key={s.id} role="option" aria-selected={i===active}><button className={i===active?'on':''} onMouseDown={e=>e.preventDefault()} onClick={()=>pick(s)}>
    <b>{s.code}</b><span>{s.name} · {Number(s.power_kva)} kVA · {s.line_count} jur</span></button></li>)}
   {!items.length&&<li className="mf-pick-empty">{busy?'Mencari…':q?'Tidak ada gardu yang cocok':'Ketik nomor gardu'}</li>}
   {value&&<li><button className="mf-pick-cancel" onMouseDown={e=>e.preventDefault()} onClick={()=>setOpen(false)}>Batal</button></li>}
  </ul>}
 </div>;
}
