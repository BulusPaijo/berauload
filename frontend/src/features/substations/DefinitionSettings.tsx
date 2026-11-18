import {useState} from 'react';
import {api} from '../../api';
import type {Def,Definitions} from './types';

const labels:Record<string,string>={params:'Parameter',sessions:'Sesi',flags:'Flag non-angka',fields:'Atribut tambahan',ownership:'Kepemilikan',purpose:'Peruntukan'};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
type Form={code:string;name:string;unit:string;scope:string;display_order:number;
 min_value:string;max_value:string;required:boolean;active:boolean;kind:string;options:string};
const blank:Form={code:'',name:'',unit:'A',scope:'line',display_order:0,
 min_value:'',max_value:'',required:false,active:true,kind:'text',options:''};
const formFrom=(row:Def):Form=>({...blank,...row,min_value:row.min_value==null?'':String(row.min_value),
 max_value:row.max_value==null?'':String(row.max_value),options:(row.options||[]).join(', '),kind:row.kind||'text'});

export default function DefinitionSettings({defs,reload}:{defs:Definitions;reload:()=>void}){
 const [kind,setKind]=useState<keyof Definitions>('params');
 const [form,setForm]=useState<Form>(blank),[editing,setEditing]=useState<number|null>(null);
 const [dialog,setDialog]=useState(false),[error,setError]=useState('');
 const change=(key:keyof Form,value:string|number|boolean)=>setForm(s=>({...s,[key]:value}));
 const open=(row?:Def)=>{setEditing(row?.id??null);setForm(row?formFrom(row):{...blank});setError('');setDialog(true)};
 const close=()=>{setDialog(false);setError('')};
 async function save(){
  if(!form.name.trim()||(!editing&&!form.code.trim())){setError('Kode dan nama wajib diisi');return}
  const minimum=form.min_value===''?null:Number(form.min_value);
  const maximum=form.max_value===''?null:Number(form.max_value);
  if(kind==='params'&&((minimum!==null&&!Number.isFinite(minimum))||
      (maximum!==null&&!Number.isFinite(maximum))||
      (minimum!==null&&maximum!==null&&minimum>maximum))){
   setError('Batas minimum harus angka dan tidak boleh lebih besar dari maksimum');return;
  }
  const body:Record<string,unknown>={name:form.name.trim(),display_order:Number(form.display_order),active:form.active};
  if(!editing)body.code=form.code.trim();
  if(kind==='params')Object.assign(body,{unit:form.unit,scope:form.scope,
   min_value:minimum,max_value:maximum,required:form.required});
  if(kind==='fields')Object.assign(body,{kind:form.kind,
   options:form.options.split(',').map(s=>s.trim()).filter(Boolean)});
  try{
   await api(`/substations/definitions/${kind}${editing?`/${editing}`:''}`,
    {method:editing?'PATCH':'POST',body:JSON.stringify(body)});
   reload();close();
  }catch(e){setError(msg(e))}
 }
 return <div className="substation-stack">
  <section className="substation-section-heading"><div><span className="substation-kicker">PENGATURAN GLOBAL · ADMIN</span><h3>Definisi Pengukuran</h3><p>Parameter, sesi, dan status digunakan bersama seluruh ULP/KP. Kode tetap permanen.</p></div>
   <button className="btn primary" onClick={()=>open()}>+ Tambah {labels[kind]}</button></section>
  <nav className="substation-switch" aria-label="Jenis definisi">{Object.keys(labels).map(key=><button key={key}
   className={kind===key?'active':''} onClick={()=>{setKind(key as keyof Definitions);close()}}>{labels[key]}</button>)}</nav>
  <section className="substation-surface"><div className="substation-surface-head"><strong>{labels[kind]} ({defs[kind].length})</strong><span>Klik Ubah untuk mengedit tanpa mengubah kode</span></div>
   <div className="scroll-table"><table><thead><tr><th>Kode permanen</th><th>Nama</th>{kind==='params'&&<><th>Satuan</th><th>Batas wajar</th></>}<th>Urutan</th><th>Status</th><th>Aksi</th></tr></thead><tbody>{defs[kind].map(row=><tr key={row.id}><td><code>{row.code}</code></td><td><strong>{row.name}</strong></td>
    {kind==='params'&&<><td>{row.unit||'—'}</td><td>{row.min_value??'—'} – {row.max_value??'—'}</td></>}
    <td>{row.display_order}</td><td><span className={'substation-chip '+(row.active?'success':'muted')}>{row.active?'Aktif':'Arsip'}</span></td><td><button className="btn secondary sm" onClick={()=>open(row)}>Ubah</button></td></tr>)}
    {!defs[kind].length&&<tr><td colSpan={7}>Belum ada definisi pada kategori ini</td></tr>}</tbody></table></div>
  </section>
  {dialog&&<div className="substation-modal-backdrop"><section className="substation-modal" role="dialog" aria-modal="true" aria-label={editing?'Ubah definisi':'Tambah definisi'}>
   <div className="substation-surface-head"><div><span className="substation-kicker">{editing?'EDIT DEFINISI':'DEFINISI BARU'}</span><h3>{editing?'Ubah':'Tambah'} {labels[kind]}</h3></div><button className="btn secondary sm" onClick={close} aria-label="Tutup">✕</button></div>
   {error&&<div className="notice error" role="alert">{error}</div>}
   <div className="substation-form"><label>Kode permanen<input disabled={!!editing} value={form.code} onChange={e=>change('code',e.target.value)}/></label>
    <label>Nama<input value={form.name} onChange={e=>change('name',e.target.value)}/></label>
    {kind==='params'&&<><label>Satuan<input value={form.unit} onChange={e=>change('unit',e.target.value)}/></label>
     <label>Cakupan<select value={form.scope} onChange={e=>change('scope',e.target.value)} disabled={!!editing}><option value="line">Per jurusan</option><option value="substation">Per gardu</option></select></label>
     <label>Min wajar<input type="number" value={form.min_value} onChange={e=>change('min_value',e.target.value)}/></label>
     <label>Max wajar<input type="number" value={form.max_value} onChange={e=>change('max_value',e.target.value)}/></label>
     <label className="substation-check"><input type="checkbox" checked={form.required} onChange={e=>change('required',e.target.checked)}/>Wajib diisi</label></>}
    {kind==='fields'&&<><label>Tipe<select value={form.kind} onChange={e=>change('kind',e.target.value)}><option value="text">Teks</option><option value="number">Angka</option><option value="choice">Pilihan</option></select></label>
     <label>Opsi (pisah koma)<input value={form.options} onChange={e=>change('options',e.target.value)}/></label></>}
    <label>Urutan<input type="number" value={form.display_order} onChange={e=>change('display_order',Number(e.target.value))}/></label>
    <label className="substation-check"><input type="checkbox" checked={form.active} onChange={e=>change('active',e.target.checked)}/>Aktif</label>
   </div><div className="substation-dialog-actions"><button className="btn secondary" onClick={close}>Batal</button><button className="btn primary" onClick={save}>Simpan definisi</button></div>
  </section></div>}
 </div>;
}
