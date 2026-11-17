import {useBranding} from '../branding/BrandingContext';
import {safeBrandSlug} from '../branding/branding.mjs';
import {useEffect,useState} from 'react';
import {api,apiFetch,isoWita,csrf} from '../../api';
import './template-import.css';

type Tab={code:string;name:string;parameters:number};
type Configuration={unit:{id:number;code:string;name:string};tabs:Tab[]};
type Counts=Record<'inserted'|'same'|'different'|'locked'|'skipped_hour',number>;
type ParameterCounts=Counts&{code:string};
type Difference={day:string;hour:number;code:string;existing:string;uploaded:string};
type Preview={token:string;mode:string;hours_to_write:number;values_found:number;
  counts:Partial<Counts>;by_parameter:ParameterCounts[];differences:Difference[];
  period:{start:string;end:string}};
type ImportRow={id:string;filename:string;kind:string;year:number;month:number;
  created_at:string;readings_created:number;hours_created:number};
type FileError={sheet:string;cell:string;message:string};

async function previewFile(file:File,mode:string):Promise<Preview>{
  const form=new FormData();form.append('file',file);form.append('mode',mode);
  // Multipart is automatically given its boundary by fetch.
  const result=await apiFetch('/api/template-import/preview',{
    method:'POST',body:form,credentials:'same-origin',headers:{'X-CSRF-Token':csrf},
  });
  const body=await result.json().catch(()=>({}));
  if(!result.ok){
    const detail=body.detail;
    if(detail?.errors){const lines=(detail.errors as FileError[]).map(
      e=>`${e.sheet}!${e.cell}: ${e.message}`);
      throw Object.assign(new Error(detail.message||'File tidak valid'),{issues:lines});}
    throw new Error(typeof detail==='string'?detail:`HTTP ${result.status}`);
  }
  return body as Preview;
}

export default function TemplateImportPage(){
 const {branding}=useBranding();
  const [config,setConfig]=useState<Configuration|null>(null);
  const [selected,setSelected]=useState<string[]>([]);
  const [start,setStart]=useState(isoWita());
  const [end,setEnd]=useState(isoWita());
  const [mode,setMode]=useState('fill_empty');
  const [file,setFile]=useState<File|null>(null);
  const [preview,setPreview]=useState<Preview|null>(null);
  const [history,setHistory]=useState<ImportRow[]>([]);
  const [errors,setErrors]=useState<string[]>([]);
  const [status,setStatus]=useState('');
  const [working,setWorking]=useState(false);
  function refreshHistory(){api<ImportRow[]>('/template-import/history').then(setHistory).catch(()=>{});}
  useEffect(()=>{api<Configuration>('/template-import/config').then(c=>{
    setConfig(c);setSelected(c.tabs.map(t=>t.code));
  }).catch(e=>setErrors([String(e)]));refreshHistory()},[]);
  async function download(){
    setErrors([]);setStatus('');setWorking(true);
    try{
      const params=new URLSearchParams({start,end,tabs:selected.join(',')});
      const r=await apiFetch('/api/template-import/template?'+params.toString(),{credentials:'same-origin'});
      if(!r.ok){const body=await r.json().catch(()=>({}));throw new Error(body.detail||`HTTP ${r.status}`)}
      const blob=await r.blob();const url=URL.createObjectURL(blob);
      const a=document.createElement('a');a.href=url;
      a.download=`${safeBrandSlug(branding.app_short_name)}_Template_${config?.unit.code}_${start}_${end}.xlsx`;
      a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
      setStatus('Template berhasil diunduh. Isi sel kuning pada Excel lalu unggah kembali.');
    }catch(e){setErrors([String(e instanceof Error?e.message:e)])}
    finally{setWorking(false)}
  }
  async function checkFile(){
    if(!file)return;setWorking(true);setErrors([]);setPreview(null);setStatus('');
    try{setPreview(await previewFile(file,mode))}
    catch(e){const details=(e as Error&{issues?:string[]}).issues;
      setErrors(details?.length?details:[String(e instanceof Error?e.message:e)])}
    finally{setWorking(false)}
  }
  async function commit(){
    if(!preview)return;setWorking(true);setErrors([]);
    try{
      const result=await api<{readings_created:number;computed_created:number}>('/template-import/commit',{
        method:'POST',body:JSON.stringify({token:preview.token})});
      setStatus(`Import berhasil: ${result.readings_created} pembacaan baru (${result.computed_created} computed).`);
      setPreview(null);setFile(null);refreshHistory();
    }catch(e){setErrors([String(e instanceof Error?e.message:e)])}
    finally{setWorking(false)}
  }
  return <div className="template-import page-space">
    <div className="page-top"><div><div className="eyebrow">IMPORT PER JAM · WITA</div>
      <h2>Template {branding.app_short_name}</h2><p>Unduh template berdasarkan form input aktif, isi, lalu periksa sebelum menyimpan.</p>
    </div></div>
    {config&&<div className="template-panel"><h3>1. Unduh template</h3>
      <p>Unit tujuan: <strong>{config.unit.name}</strong> ({config.unit.code}). Belum ada pemilih unit pada tahap ini.</p>
      <div className="template-fields"><label>Mulai<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Selesai<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
      <div className="template-tabs" aria-label="Pilih tab form input">
        {config.tabs.map(t=><label key={t.code}><input type="checkbox" checked={selected.includes(t.code)}
          onChange={e=>setSelected(old=>e.target.checked?[...old,t.code]:old.filter(c=>c!==t.code))}/>
          {t.name} <small>({t.parameters} parameter)</small></label>)}
      </div><button className="btn primary" disabled={working||!selected.length} onClick={download}>Unduh .xlsx</button>
    </div>}
    <div className="template-panel"><h3>2. Unggah dan pratinjau</h3>
      <label className="template-upload">File .xlsx (maksimum 15 MB)
        <input type="file" accept=".xlsx" onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null)}}/></label>
      <div className="template-fields"><label>Mode import<select value={mode} onChange={e=>{setMode(e.target.value);setPreview(null)}}>
        <option value="fill_empty">Isi sel yang masih kosong (bawaan)</option>
        <option value="new_hours">Hanya jam baru di unit tujuan</option>
      </select></label></div>
      <p className="muted small">Tidak ada mode timpa. Hari verified/final dan pembacaan yang telah ada tidak diubah.</p>
      <button className="btn primary" disabled={!file||working} onClick={checkFile}>Periksa File</button>
    </div>
    {!!errors.length&&<div className="template-panel template-error" role="alert"><strong>File ditolak / terjadi kesalahan</strong>
      <div className="template-scroll">{errors.slice(0,200).map((e,i)=><p key={i}>{e}</p>)}</div></div>}
    {!!status&&<p className="template-message">{status}</p>}
    {preview&&<div className="template-panel"><h3>3. Hasil pratinjau</h3>
      <p>Periode {preview.period.start} – {preview.period.end} · {preview.values_found} angka · {preview.hours_to_write} slot akan diisi</p>
      <div className="template-stats">{(['inserted','same','different','locked','skipped_hour'] as const).map(key=>
        <div key={key}><span>{({inserted:'Akan disisipkan',same:'Sama',different:'Berbeda',locked:'Terkunci',skipped_hour:'Jam dilewati'})[key]}</span>
          <b>{preview.counts[key]||0}</b></div>)}</div>
      <div className="scroll-table"><table><thead><tr><th>Parameter</th><th>Baru</th><th>Sama</th><th>Berbeda</th><th>Terkunci</th><th>Jam dilewati</th></tr></thead>
        <tbody>{preview.by_parameter.map(row=><tr key={row.code}><td>{row.code}</td><td>{row.inserted}</td><td>{row.same}</td>
          <td>{row.different}</td><td>{row.locked}</td><td>{row.skipped_hour}</td></tr>)}</tbody></table></div>
      {!!preview.differences.length&&<details><summary>Perbedaan (maks. 200)</summary>
        <div className="template-scroll">{preview.differences.map((d,i)=><p key={i}>
          {d.day} {String(d.hour).padStart(2,'0')}:00 · {d.code}: tersimpan {d.existing}, file {d.uploaded}</p>)}</div></details>}
      <button className="btn primary" disabled={working} onClick={commit}>Konfirmasi Import (Tanpa Timpa)</button>
    </div>}
    <div className="template-panel"><h3>Riwayat Import (Semua Jenis)</h3>
      <div className="scroll-table"><table><thead><tr><th>Waktu</th><th>Jenis</th><th>File</th><th>Periode awal</th><th>Nilai baru</th></tr></thead>
        <tbody>{history.map(r=><tr key={r.id}><td>{r.created_at?.slice(0,19).replace('T',' ')}</td>
          <td>{r.kind==='template'?'Template {branding.app_short_name}':'Laporan lama'}</td>
          <td>{r.filename}</td><td>{r.year}-{String(r.month).padStart(2,'0')}</td>
          <td>{r.readings_created}</td></tr>)}</tbody></table></div>
    </div>
  </div>
}
