import {useCallback,useEffect,useMemo,useState} from 'react';
import {Download,Eye} from 'lucide-react';
import {api,apiFetch,csrf,activeUnitId} from '../../../api';
import {useBranding} from '../../branding/BrandingContext';
import {safeBrandSlug} from '../../branding/branding.mjs';
import {fromQuery} from '../analysis/helpers.mjs';
import type {AnalysisDefinitions} from '../analysis/types';
import {buildSpec,filterBody,fromTemplate,sizeNote,validateSpec} from './spec.mjs';
import type {CatalogItem,ExportColumn} from './spec.mjs';
import ExportColumns from './ExportColumns';
import ExportFilter from './ExportFilter';
import ExportTemplates from './ExportTemplates';
import type {Template} from './ExportTemplates';
import '../../data-export/export-builder.css';
import './export.css';

type Catalog={columns:CatalogItem[];limits:{wide:number;long:number;preview:number}};
type Preview={headers:string[];rows:(string|number|null)[][];total:number;limit:number;over_limit:boolean};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
const DEFAULT_KEYS=['code','name','feeder','power_kva','measured_on','session','calc:persen_beban','category'];
export default function ExportPage({admin,userId}:{admin:boolean;userId:number}){
 const {branding}=useBranding();
 const [catalog,setCatalog]=useState<Catalog|null>(null),[defs,setDefs]=useState<AnalysisDefinitions|null>(null);
 const [templates,setTemplates]=useState<Template[]>([]);
 const [filter,setFilter]=useState<Record<string,string|string[]>>(()=>fromQuery(location.search));
 const [columns,setColumns]=useState<ExportColumn[]>([]),[shape,setShape]=useState<'wide'|'long'>('wide');
 const [format,setFormat]=useState<'xlsx'|'csv'>('xlsx'),[delimiter,setDelimiter]=useState<';'|','>(';');
 const [preview,setPreview]=useState<Preview|null>(null),[busy,setBusy]=useState(false);
 const [error,setError]=useState(''),[notice,setNotice]=useState('');
 const [tplId,setTplId]=useState(''),[tplName,setTplName]=useState('Ekspor gardu'),[tplShared,setTplShared]=useState(false);
 const unit=activeUnitId();
 const reloadTemplates=useCallback(()=>api<Template[]>('/substations/export/templates').then(setTemplates),[]);
 useEffect(()=>{
  let active=true;setError('');
  Promise.all([api<Catalog>('/substations/export/catalog'),api<AnalysisDefinitions>('/substations/analysis/definitions'),
   api<Template[]>('/substations/export/templates')]).then(([c,d,t])=>{if(!active)return;
    setCatalog(c);setDefs(d);setTemplates(t);
    const known=new Set(c.columns.map(i=>i.key));
    setColumns(old=>old.length?old:DEFAULT_KEYS.filter(k=>known.has(k)).map(key=>({key})));
   }).catch(e=>{if(active)setError(msg(e))});
  return()=>{active=false};
 },[unit]);
 const keys=useMemo(()=>new Set(catalog?.columns.map(i=>i.key)),[catalog]);
 const spec=buildSpec({columns,shape,format,delimiter});
 const problems=catalog?validateSpec({columns,shape},keys):[];
 const body=()=>JSON.stringify({filter:filterBody(filter),spec});
 const limit=catalog?.limits[shape]??0;
 function touch(){setPreview(null);setError('');setNotice('');}
 async function showPreview(){setBusy(true);touch();
  try{setPreview(await api<Preview>('/substations/export/preview',{method:'POST',body:body()}));}
  catch(e){setError(msg(e))}finally{setBusy(false)}}
 async function download(){setBusy(true);touch();
  try{const r=await apiFetch('/api/substations/export/download',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body()});
   if(!r.ok){const b=await r.json().catch(()=>({}));throw new Error(b.detail||`HTTP ${r.status}`)}
   const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');
   a.href=url;a.download=`${safeBrandSlug(branding.app_short_name)}_gardu_${new Date().toISOString().slice(0,10)}.${format}`;
   document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);setNotice('Berkas disiapkan. Periksa folder unduhan browser.');
  }catch(e){setError(msg(e))}finally{setBusy(false)}}
 function loadTemplate(id:string){setTplId(id);const t=templates.find(x=>String(x.id)===id);if(!t)return;
  const r=fromTemplate(t,keys);setColumns(r.columns);setShape(r.shape);setFormat(r.format);setDelimiter(r.delimiter);
  setTplName(t.name);setTplShared(t.shared);touch();}
 async function saveTemplate(){setBusy(true);setError('');
  try{const t=await api<Template>('/substations/export/templates',{method:'POST',body:JSON.stringify({name:tplName,shared:tplShared,spec})});
   await reloadTemplates();setTplId(String(t.id));setNotice('Template disimpan.');}catch(e){setError(msg(e))}finally{setBusy(false)}}
 async function updateTemplate(){const t=templates.find(x=>String(x.id)===tplId);if(!t)return;setBusy(true);setError('');
  try{await api(`/substations/export/templates/${t.id}`,{method:'PUT',body:JSON.stringify({name:tplName,shared:t.shared,spec,expected_version:t.version})});
   await reloadTemplates();setNotice('Template diperbarui.');}catch(e){setError(msg(e))}finally{setBusy(false)}}
 async function archiveTemplate(){const t=templates.find(x=>String(x.id)===tplId);if(!t)return;
  if(!window.confirm('Arsipkan template ini? Data pengukuran tidak berubah.'))return;
  try{await api(`/substations/export/templates/${t.id}/archive`,{method:'POST'});setTplId('');await reloadTemplates();}catch(e){setError(msg(e))}}
 if(!catalog||!defs)return error?<div className="notice error" role="alert">{error}</div>:<p role="status">Memuat pilihan kolom…</p>;
 const note=preview?sizeNote(preview.total,preview.limit):null;
 return <div className="export-builder gardu-export">
  <div className="gardu-section-head"><div><div className="eyebrow">Pengukuran gardu · Export</div><h3>Export Data Gardu</h3><p>Pilih gardu, kolom, dan bentuk berkas. Lihat contoh dulu sebelum mengunduh. Data pengukuran tidak diubah.</p></div></div>
  {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice success" role="status">{notice}</div>}
  <ExportFilter defs={defs} filter={filter} onChange={f=>{setFilter(f);touch()}} onUseAnalysis={()=>{setFilter(fromQuery(location.search));touch()}}/>
  <section className="panel export-section"><h3>Bentuk berkas</h3><div className="export-fields">
   <label>Bentuk data<select value={shape} onChange={e=>{setShape(e.target.value as 'wide'|'long');touch()}}><option value="wide">Lebar: satu baris per gardu</option><option value="long">Panjang: satu baris per nilai ukur</option></select></label>
   <label>Format<select value={format} onChange={e=>{setFormat(e.target.value as 'xlsx'|'csv');touch()}}><option value="xlsx">Excel (.xlsx)</option><option value="csv">CSV (.csv)</option></select></label>
   {format==='csv'&&<label>Pemisah CSV<select value={delimiter} onChange={e=>setDelimiter(e.target.value as ';'|',')}><option value=";">Titik koma (;)</option><option value=",">Koma (,)</option></select></label>}
  </div>{shape==='long'&&<p className="muted small">Bentuk panjang menambahkan kolom Parameter, Satuan, Jurusan, Nilai, dan Penanda di ujung kanan.</p>}</section>
  <ExportColumns items={catalog.columns} columns={columns} shape={shape} onChange={c=>{setColumns(c);touch()}}/>
  <section className="panel export-section"><h3>Contoh dan unduh</h3>
   {!!problems.length&&<ul className="export-problems">{problems.map(p=><li key={p}>{p}</li>)}</ul>}
   <div className="export-actions"><button className="btn secondary" disabled={busy||!!problems.length} onClick={showPreview}><Eye size={17}/> Lihat {catalog.limits.preview} baris contoh</button>
    <button className="btn primary" disabled={busy||!!problems.length||!!preview?.over_limit} onClick={download}><Download size={17}/> {busy?'Memproses…':'Unduh '+format.toUpperCase()}</button></div>
   {preview&&note&&<p className={'export-size '+note.level} role="status">{note.text}</p>}
   {preview&&<div className="scroll-table"><table><thead><tr>{preview.headers.map((h,i)=><th key={i}>{h}</th>)}</tr></thead>
    <tbody>{preview.rows.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{v==null?'—':String(v)}</td>)}</tr>)}</tbody></table></div>}
   <p className="muted small">Sel kosong ditulis kosong, bukan nol. Lembar “Keterangan” memuat filter, versi definisi, dan rumus kolom hitung.</p>
  </section>
  <ExportTemplates templates={templates} selected={tplId} name={tplName} shared={tplShared} admin={admin} userId={userId} busy={busy} valid={!problems.length}
   onSelect={loadTemplate} onName={setTplName} onShared={setTplShared} onSave={saveTemplate} onUpdate={updateTemplate} onArchive={archiveTemplate}/>
 </div>;
}
