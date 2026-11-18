import {useActionDialog} from './ActionDialog';
import {useCallback,useEffect,useMemo,useState} from 'react';
import Drawer from './ui/Drawer';
import KeyValueEditor from './ui/KeyValueEditor';
import FileDrop from './ui/FileDrop';
import {api,apiFetch,activeUnitId,downloadApi} from '../../api';
import type {User} from '../../api';
import type {Definitions,Feeder,Page,Substation} from './types';
import {useScope} from './scope';
import {editableBody,formFromRow} from './masterForm.mjs';

type Props={user:User;defs:Definitions;feeders:Feeder[];reloadDefinitions:()=>void;
 readonly:boolean;initialSearch?:string};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const cols=['code','name','feeder_id','power_kva','phase','line_count','ownership','purpose','brand','active'] as const;
const labels:Record<string,string>={code:'Kode',name:'Nama Gardu',feeder_id:'Penyulang',power_kva:'kVA',phase:'Fase',line_count:'Jurusan',ownership:'Kepemilikan',purpose:'Peruntukan',brand:'Merek',active:'Aktif'};
const blank={unit_id:'',code:'',name:'',feeder_id:'',power_kva:'',phase:'3',line_count:'1',ownership:'PLN',purpose:'UMUM',address:'',brand:'',tap:'',serial_number:'',year:'',lat:'',lon:'',line_labels:'',extra_values:'{}'};
const FORM_GROUPS:{title:string;fields:[string,string,string?,boolean?][]}[]=[
 {title:'Identitas',fields:[['code','Kode *','Permanen, tidak bisa diubah'],['name','Nama *'],['feeder_id','Penyulang *',undefined,true],['address','Alamat',undefined,true]]},
 {title:'Trafo',fields:[['power_kva','Daya (kVA) *'],['phase','Fase'],['line_count','Jumlah jurusan *','1 sampai 5'],['line_labels','Label jurusan','Pisahkan dengan |']]},
 {title:'Lokasi',fields:[['lat','Latitude','Contoh 2.1534'],['lon','Longitude','Contoh 117.4912']]},
 {title:'Rincian',fields:[['ownership','Kepemilikan'],['purpose','Peruntukan'],['brand','Merk'],['tap','Tap'],['serial_number','Nomor seri'],['year','Tahun']]}];
export default function MasterPanel({user,defs,feeders,readonly:viewOnly,reloadDefinitions,initialSearch}:Props){
 const scope=useScope();
 const readonly=viewOnly||!scope?.can_manage_master;
 const units=scope?.units??[];const unitName=(id:number)=>units.find(u=>u.id===id)?.name??'—';
 const [formError,setFormError]=useState('');
 const {confirm:askConfirm,prompt:askText,dialog}=useActionDialog();
 const unitId=activeUnitId()??0;
 const [records,setRecords]=useState<Substation[]>([]),[total,setTotal]=useState(0);
 const [page,setPage]=useState(1),[q,setQ]=useState(initialSearch??''),[feederFilter,setFeederFilter]=useState('');
 const [sort,setSort]=useState('code'),[desc,setDesc]=useState(false),[showArchived,setShowArchived]=useState(false);
 const [selected,setSelected]=useState<number[]>([]),[visible,setVisible]=useState<string[]>(()=>{try{
  const text=localStorage.getItem(`berauload:substation_columns:${user.id}`);
  return text?JSON.parse(text):[...cols];}catch{return [...cols]}});
 const [form,setForm]=useState<Record<string,string>>(blank),[editing,setEditing]=useState<number|null>(null);
 const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState<any>(null);
 const [applyExisting,setApplyExisting]=useState(false),[newFeeders,setNewFeeders]=useState(false);
 const [message,setMessage]=useState(''),[bulkField,setBulkField]=useState('feeder_id'),[bulkValue,setBulkValue]=useState('');
 const [feederName,setFeederName]=useState(''),[feederCode,setFeederCode]=useState('');
 const [lineWarning,setLineWarning]=useState<{count:number;ids:number[];changes:Record<string,unknown>;bulk:boolean}|null>(null);
 const ownFeeders=feeders;
 const feederNameByIdAll=(id:number|null)=>feeders.find(f=>f.id===id)?.name||'—';
 const colNames=visible.filter(v=>cols.includes(v as typeof cols[number]));
 async function load(){try{const query=new URLSearchParams({page:String(page),page_size:'50',
  q,sort,desc:String(desc),active:String(!showArchived)});
  if(feederFilter)query.set('feeder_id',feederFilter);
  const result=await api<Page<Substation>>('/substations/master?'+query);
  setRecords(result.items);setTotal(result.total);setSelected([]);
 }catch(e){setMessage(msg(e))}}
 useEffect(()=>{void load()},[unitId,page,q,feederFilter,sort,desc,showArchived]);
 const feederNameById=feederNameByIdAll;
 const toggleCol=(column:string)=>{const next=visible.includes(column)?visible.filter(x=>x!==column):[...visible,column];
  setVisible(next);try{localStorage.setItem(`berauload:substation_columns:${user.id}`,JSON.stringify(next))}catch{}};
 const [drawer,setDrawer]=useState<'form'|'import'|null>(null);
 const closeDrawer=useCallback(()=>{setDrawer(null);setEditing(null);setForm({...blank});},[]);
 const startEdit=(row?:Substation)=>{setDrawer('form');setEditing(row?.id??null);
  setFormError('');setForm(row?formFromRow(blank,row):{...blank,unit_id:String(unitId)});};
 async function applyMaster(body:Record<string,unknown>,confirm=false){
  if(!editing)return api('/substations/master',{method:'POST',body:JSON.stringify(body)});
  delete body.code;
  const response=await apiFetch(`/api/substations/master/${editing}`,{method:'PATCH',
   body:JSON.stringify({...body,confirm_line_reduction:confirm})});
  const result=await response.json().catch(()=>({}));
  if(!response.ok){
   const detail=result.detail;
   if(response.status===409&&detail?.code==='LINE_REDUCTION_CONFIRM_REQUIRED'){
    setLineWarning({count:detail.affected_values,ids:[editing],changes:body,bulk:false});return null;
   }
   throw new Error(typeof detail==='string'?detail:Array.isArray(detail)?detail.map((d:{msg?:string;loc?:unknown[]})=>`${(d.loc??[]).slice(-1)}: ${d.msg}`).join('; '):detail?.message||`HTTP ${response.status}`);
  }
  return result;
 }
 async function save(){setFormError('');try{const body=editableBody(form,!editing,units.length>1);
  const result=await applyMaster(body);if(result===null)return;
  setMessage('Master berhasil disimpan');setForm({...blank});setEditing(null);setDrawer(null);await load();
 }catch(e){setFormError(msg(e))}}
 async function patchBulk(ids:number[],changes:Record<string,unknown>){
  return api<{results:{id:number;status:string;reason?:string;affected_values?:number}[]}>('/substations/master/bulk',{
   method:'PATCH',body:JSON.stringify({ids,changes})});
 }
 async function doBulk(){if(!selected.length||!(await askConfirm(`Perbarui ${selected.length} gardu?`)))return;
  try{let value:unknown=bulkValue;if(bulkField==='feeder_id')value=bulkValue?Number(bulkValue):null;
   if(bulkField==='line_count')value=Number(bulkValue);
   if(bulkField==='active')value=bulkValue==='true';
   if(bulkField==='unit_id')value=Number(bulkValue);
   const changes={[bulkField]:value};const response=await patchBulk(selected,changes);
   const pending=response.results.filter(r=>r.status==='needs_confirmation');
   if(pending.length)setLineWarning({ids:pending.map(r=>r.id),count:pending.reduce((n,r)=>n+(r.affected_values||0),0),changes,bulk:true});
   setMessage(`Hasil: ${response.results.filter(r=>r.status==='updated').length} berubah; ${response.results.filter(r=>r.status==='error').length} gagal; ${pending.length} perlu konfirmasi`);
   await load();
  }catch(e){setMessage(msg(e))}}
 async function confirmReduction(){const pending=lineWarning;if(!pending)return;
  try{
   if(pending.bulk){const result=await patchBulk(pending.ids,{...pending.changes,confirm_line_reduction:true});
    setMessage(`Konfirmasi pengurangan jurusan: ${result.results.filter(r=>r.status==='updated').length} berhasil`);
   }else{
    const id=pending.ids[0];await api(`/substations/master/${id}`,{method:'PATCH',
     body:JSON.stringify({...pending.changes,confirm_line_reduction:true})});
    setEditing(null);setForm({...blank});setDrawer(null);setMessage('Master berhasil disimpan; riwayat pengukuran tetap utuh');
   }
   setLineWarning(null);await load();
  }catch(e){setMessage(msg(e))}
 }
 async function addFeeder(){try{await api('/substations/feeders',{method:'POST',body:JSON.stringify({code:feederCode,name:feederName})});
  setFeederCode('');setFeederName('');reloadDefinitions();setMessage('Penyulang ditambahkan');}catch(e){setMessage(msg(e))}}
 async function inspect(){if(!file)return;const data=new FormData();data.append('file',file);
  try{setPreview(await api('/substations/master/import/preview',{method:'POST',body:data}));setMessage('Pratinjau tidak mengubah database');}
  catch(e){setMessage(msg(e))}}
 async function apply(){if(!preview||!(await askConfirm('Terapkan hasil pratinjau ke master gardu?')))return;
  try{const result=await api<any>('/substations/master/import/apply',{method:'POST',
   body:JSON.stringify({token:preview.token,update_existing:applyExisting,create_feeders:newFeeders})});
   setMessage(JSON.stringify(result.results.slice(0,15)));setPreview(null);reloadDefinitions();await load();
  }catch(e){setMessage(msg(e))}}
 return <div className="substation-stack">{dialog}
  <div className="substation-section-heading"><div><span className="substation-kicker">PENGUKURAN GARDU · MASTER</span><h3>Master Gardu Distribusi</h3><p>Kelola identitas gardu, penyulang, kapasitas trafo, dan jumlah jurusan.</p></div><span className="substation-chip success">{total} gardu</span></div>
  {lineWarning&&<div className="substation-modal-backdrop"><section className="substation-modal" role="dialog" aria-modal="true" aria-label="Konfirmasi pengurangan jurusan">
   <span className="substation-kicker">KONFIRMASI PERUBAHAN MASTER</span><h3>Kurangi jumlah jurusan?</h3>
   <p>Perubahan ini berpengaruh pada <strong>{lineWarning.count} nilai historis</strong> di {lineWarning.ids.length} gardu. Nilai dan snapshot pengukuran lama <strong>tidak akan dihapus</strong>, tetapi jurusan yang dikurangi tidak tersedia untuk pengukuran baru.</p>
   <div className="substation-dialog-actions"><button className="btn secondary" onClick={()=>setLineWarning(null)}>Batal</button><button className="btn primary" onClick={confirmReduction}>Ya, lanjutkan perubahan</button></div>
  </section></div>}
  <div className="substation-controls"><label>Cari gardu<input placeholder="Kode atau nama" value={q} onChange={e=>{setQ(e.target.value);setPage(1)}}/></label>
   <label>Penyulang<select value={feederFilter} onChange={e=>{setFeederFilter(e.target.value);setPage(1)}}><option value="">Semua</option>{ownFeeders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
   <label><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/> Lihat arsip</label>
   {!readonly&&<button className="btn secondary" onClick={()=>setDrawer('import')}>Impor dari Excel</button>}{!readonly&&<button className="btn primary" onClick={()=>startEdit()}>+ Tambah gardu</button>}
   <button className="btn secondary" onClick={()=>void downloadApi('/substations/master/template','master_gardu.xlsx')}>Unduh Template</button>
  </div>
  {message&&<div className="notice info">{message}</div>}
  <div className="substation-controls"><strong>Kolom ditampilkan</strong>{cols.map(c=><label key={c} className="substation-check"><input type="checkbox" checked={visible.includes(c)} onChange={()=>toggleCol(c)}/>{labels[c]}</label>)}</div>
  <div className="scroll-table"><table><thead><tr><th><input type="checkbox" checked={!!records.length&&records.every(r=>selected.includes(r.id))} onChange={e=>setSelected(e.target.checked?records.map(r=>r.id):[])}/></th>
  {units.length>1&&<th>Unit</th>}{colNames.map(c=><th key={c}><button className="link-btn" onClick={()=>{setSort(c==='power_kva'||c==='feeder_id'||c==='name'?c:'code');setDesc(!desc)}}>{labels[c]}</button></th>)}<th>Aksi</th></tr></thead><tbody>{records.map(r=><tr key={r.id}><td><input type="checkbox" checked={selected.includes(r.id)} onChange={e=>setSelected(e.target.checked?[...selected,r.id]:selected.filter(id=>id!==r.id))}/></td>
   {units.length>1&&<td>{unitName(r.unit_id)}</td>}{colNames.map(c=><td key={c}>{c==='feeder_id'?feederNameById(r.feeder_id):String(r[c as keyof Substation]??'—')}</td>)}
   <td><button className="btn secondary sm" disabled={readonly} onClick={()=>startEdit(r)}>Ubah</button></td></tr>)}</tbody></table>
   {!records.length&&<div className="empty">Belum ada gardu pada filter ini.</div>}
  </div>
  <div className="substation-toolbar"><span>{total} gardu · halaman {page}</span><button className="btn secondary sm" disabled={page===1} onClick={()=>setPage(page-1)}>Sebelumnya</button><button className="btn secondary sm" disabled={page*50>=total} onClick={()=>setPage(page+1)}>Berikutnya</button></div>
  {!readonly&&total>records.length&&<button className="btn secondary" onClick={async()=>{try{const ids:number[]=[];for(let p=1;p<=Math.ceil(total/200)&&ids.length<500;p++){const query=new URLSearchParams({page:String(p),page_size:'200',q,sort,desc:String(desc),active:String(!showArchived)});if(feederFilter)query.set('feeder_id',feederFilter);const result=await api<Page<Substation>>('/substations/master?'+query);ids.push(...result.items.map(v=>v.id));}setSelected(ids.slice(0,500));if(total>500)setMessage('Pilihan dibatasi 500 gardu per aksi.');}catch(e){setMessage(msg(e))}}}>Pilih semua hasil filter (maks. 500)</button>}
  {!!selected.length&&!readonly&&<section className="panel"><h3>Aksi massal ({selected.length} gardu)</h3><div className="substation-controls">
   <select value={bulkField} onChange={e=>setBulkField(e.target.value)}>{[...(units.length>1?[['unit_id','Pindahkan ke unit']]:[]),['feeder_id','Penyulang'],['ownership','Kepemilikan'],['purpose','Peruntukan'],['line_count','Jurusan'],['active','Arsip/pulihkan']].map(([v,n])=><option key={v} value={v}>{n}</option>)}</select>
   {bulkField==='feeder_id'?<select value={bulkValue} onChange={e=>setBulkValue(e.target.value)}><option value="">Kosong</option>{ownFeeders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select>:
    bulkField==='unit_id'?<select value={bulkValue} onChange={e=>setBulkValue(e.target.value)}><option value="">Pilih unit…</option>{units.map(u=><option key={u.id} value={u.id}>{u.level.toUpperCase()} · {u.name}</option>)}</select>:
    bulkField==='active'?<select value={bulkValue} onChange={e=>setBulkValue(e.target.value)}><option value="true">Pulihkan</option><option value="false">Arsip</option></select>:
    <input value={bulkValue} onChange={e=>setBulkValue(e.target.value)}/>}
   <button className="btn primary" onClick={doBulk}>Terapkan</button></div></section>}
  {!readonly&&drawer==='form'&&<Drawer title={editing?'Ubah gardu':'Tambah gardu'} subtitle="Isian bertanda * wajib" onClose={closeDrawer}
   footer={<><button className="btn secondary" onClick={closeDrawer}>Batal</button><button className="btn primary" onClick={save}>{editing?'Simpan perubahan':'Simpan gardu'}</button></>}>
   {formError&&<div className="notice error" role="alert">{formError}</div>}
   {units.length>1&&<label className="ui-field">Unit pemilik<select value={form.unit_id??''} onChange={e=>setForm(v=>({...v,unit_id:e.target.value}))}>{units.map(u=><option key={u.id} value={u.id}>{u.level.toUpperCase()} · {u.name}</option>)}</select>
    <small>{editing?'Memindahkan gardu juga memindahkan riwayat pengukuran dan tindak lanjutnya ke unit baru.':'ULP dapat menaruh gardu di KP di bawahnya.'}</small></label>}
   {FORM_GROUPS.map(g=><div key={g.title}><div className="ui-section">{g.title}</div><div className="ui-grid2">
    {g.fields.map(([field,label,hint,full])=><label key={field} className={'ui-field'+(full?' ui-full':'')}>{label}
     {field==='feeder_id'?<select value={form[field]??''} onChange={e=>setForm(v=>({...v,[field]:e.target.value}))}><option value="">Belum dipilih</option>{ownFeeders.filter(f=>f.active).map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select>:
     field==='ownership'||field==='purpose'?<select value={form[field]??''} onChange={e=>setForm(v=>({...v,[field]:e.target.value}))}><option value="">—</option>{defs[field as 'ownership'|'purpose'].filter(f=>f.active).map(f=><option key={f.code} value={f.code}>{f.name}</option>)}</select>:
     field==='phase'?<select value={form[field]??'3'} onChange={e=>setForm(v=>({...v,phase:e.target.value}))}><option value="3">3 fasa</option><option value="1">1 fasa</option></select>:
     <input disabled={field==='code'&&!!editing} inputMode={['power_kva','line_count','year','lat','lon'].includes(field)?'decimal':undefined} value={form[field]??''} onChange={e=>setForm(v=>({...v,[field]:e.target.value}))}/>}
     {hint&&<small>{hint}</small>}</label>)}</div></div>)}
   <div className="ui-section">Atribut tambahan</div><KeyValueEditor value={form.extra_values??'{}'} onChange={json=>setForm(v=>({...v,extra_values:json}))}/>
  </Drawer>}
  {!readonly&&drawer==='import'&&<Drawer title="Impor master gardu" subtitle="Diperiksa dulu; tidak ada yang tersimpan sebelum Anda menyetujui." onClose={closeDrawer}
   footer={<><button className="btn secondary" onClick={closeDrawer}>Tutup</button><button className="btn primary" disabled={!file} onClick={inspect}>Periksa berkas</button></>}>
   <FileDrop file={file} accept=".csv,.xlsx" hint=".xlsx atau .csv, maksimal 4 MB" onFile={setFile}/>
   <p className="muted small">Belum punya format? <button className="link-btn" onClick={()=>void downloadApi('/substations/master/template','master_gardu.xlsx')}>Unduh template</button></p>
   <div className="ui-section">Langkah</div><p className="muted small">1. Pilih berkas → 2. Periksa hasil (baris sah dan galat) → 3. Konfirmasi dan terapkan.</p>
   {preview&&<><div className="scroll-table"><table><thead><tr><th>Baris</th><th>Kode</th><th>Aksi</th><th>Validasi</th></tr></thead><tbody>{preview.rows.map((r:any)=><tr key={r.row}><td>{r.row}</td><td>{r.values.code}</td><td>{r.action}</td><td>{r.errors.join('; ')||'Sah'}</td></tr>)}</tbody></table></div>
   {!!preview.new_feeders.length&&<p>Penyulang belum terdaftar: {preview.new_feeders.join(', ')}</p>}
   <label><input type="checkbox" checked={newFeeders} onChange={e=>setNewFeeders(e.target.checked)}/> Izinkan buat penyulang baru</label>
   <label><input type="checkbox" checked={applyExisting} onChange={e=>setApplyExisting(e.target.checked)}/> Perbarui kode gardu yang sudah ada</label>
   <button className="btn primary" onClick={apply}>Konfirmasi dan Terapkan</button></>}
  </Drawer>}
  {!readonly&&<section className="panel"><h3>Master Penyulang</h3><div className="substation-controls"><input placeholder="Kode penyulang" value={feederCode} onChange={e=>setFeederCode(e.target.value)}/><input placeholder="Nama penyulang" value={feederName} onChange={e=>setFeederName(e.target.value)}/><button className="btn primary" onClick={addFeeder}>Tambah</button><button className="btn secondary" onClick={()=>api('/substations/feeders/from-assets',{method:'POST'}).then(()=>reloadDefinitions()).catch(e=>setMessage(msg(e)))}>Ambil dari aset feeder</button></div>
   <div className="muted small">Perubahan nama penyulang berlaku untuk gardu aktif; snapshot pengukuran lama tidak berubah.</div>
   <div>{ownFeeders.map(f=><div key={f.id} className="substation-inline-row"><b>{f.code}</b> {f.name} <button className="btn secondary sm" onClick={async()=>{const name=await askText('Nama baru penyulang',f.name);if(!name)return;await api(`/substations/feeders/${f.id}`,{method:'PATCH',body:JSON.stringify({name})});reloadDefinitions()}}>Ubah nama</button><button className="btn secondary sm" onClick={async()=>{if(!(await askConfirm('Arsip penyulang?')))return;try{await api(`/substations/feeders/${f.id}`,{method:'PATCH',body:JSON.stringify({active:false})});reloadDefinitions()}catch(e){setMessage(msg(e))}}}>Arsip</button></div>)}</div>
  </section>}
 </div>;
}
