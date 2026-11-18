"use client";
import {useCallback,useState} from 'react';

type Prompt={message:string;initial:string;text:string;kind:'confirm'|'text';resolve:(result:boolean|string|null)=>void};
/** A single keyboard-accessible confirmation / text-dialog style for gardu screens. */
export function useActionDialog(){
 const [pending,setPending]=useState<Prompt|null>(null);
 const confirm=useCallback((message:string)=>new Promise<boolean>(resolve=>{
  setPending({message,initial:'',text:'',kind:'confirm',resolve:value=>resolve(value===true)});
 }),[]);
 const prompt=useCallback((message:string,initial='')=>new Promise<string|null>(resolve=>{
  setPending({message,initial,text:initial,kind:'text',resolve:value=>resolve(typeof value==='string'?value:null)});
 }),[]);
 const finish=(result:boolean|string|null)=>{pending?.resolve(result);setPending(null)};
 const dialog=pending?<div className="substation-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)finish(null)}}>
  <div className="substation-modal" role="dialog" aria-modal="true" aria-label={pending.kind==='confirm'?'Konfirmasi tindakan':'Masukkan teks'} onKeyDown={e=>{if(e.key==='Escape')finish(null)}}>
   <h3>{pending.kind==='confirm'?'Konfirmasi perubahan':'Ubah informasi'}</h3><p>{pending.message}</p>
   {pending.kind==='text'&&<label>Isi<input autoFocus value={pending.text} maxLength={180} onChange={e=>setPending(x=>x?{...x,text:e.target.value}:null)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();finish(pending.text)}}}/></label>}
   <div className="substation-dialog-actions"><button autoFocus={pending.kind==='confirm'} className="btn secondary" onClick={()=>finish(null)}>Batal</button>
    <button className="btn primary" disabled={pending.kind==='text'&&!pending.text.trim()} onClick={()=>finish(pending.kind==='confirm'?true:pending.text.trim())}>Lanjutkan</button></div>
  </div></div>:null;
 return {confirm,prompt,dialog};
}
