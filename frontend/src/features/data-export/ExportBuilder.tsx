import {useEffect,useMemo,useState} from 'react';
import {ArrowDown,ArrowUp,Download,Eye,FileSpreadsheet,Plus,Save,Search,Trash2} from 'lucide-react';
import {api,apiFetch,csrf,isoWita, type Catalog} from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import {SourceStatusSummary,type Status} from '../unit-references/SourceStatus';
import type {UnitItem} from '../units/UnitManager';
import './export-builder.css';

type Format='xlsx'|'csv';
type Grain='hour'|'day'|'month'|'year';
type Agg='avg'|'min'|'max';
type Spec={columns:string[];granularity:Grain;aggregation:Agg;headers:Record<string,string>;unit_overrides:Record<string,string>;format:Format};
type Template={id:number;name:string;scope:'personal'|'system';owner_id:number;version:number;spec:Spec};
type Preview={source_status?:Status;headers:string[];rows:(string|number|null)[][];note:string};
const makeDefaultSpec=(roles:Record<string,string>):Spec=>({columns:['tanggal','jam',roles['system.capacity'],roles['system.load']].filter(Boolean),granularity:'hour',aggregation:'avg',headers:{},unit_overrides:{},format:'xlsx'});
const meta:Record<string,string>={tanggal:'Tanggal (WITA)',jam:'Jam (WITA)',status:'Status Hari'};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function ExportBuilder({catalog,role}:{catalog:Catalog;role:string}){
  const today=isoWita();
  const [start,setStart]=useState(today.slice(0,8)+'01');
  const [end,setEnd]=useState(today);
  const [spec,setSpec]=useState<Spec>(()=>makeDefaultSpec(catalog.roles||{}));
  const [search,setSearch]=useState('');
  const [units,setUnits]=useState<UnitItem[]>([]);
  const [templates,setTemplates]=useState<Template[]>([]);
  const [templateId,setTemplateId]=useState('');
  const [templateName,setTemplateName]=useState('Laporan Beban Kustom');
  const [scope,setScope]=useState('personal');
  const [preview,setPreview]=useState<Preview|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const references=useUnitMetricReferences();
  const selectedMetrics=metricsForSelection(references,catalog.metrics);
  const all=useMemo(()=>[...Object.entries(meta).map(([code,name])=>({code,name,unit:''})),...selectedMetrics], [selectedMetrics]);
  const names=new Map(all.map(m=>[m.code,'label' in m ? String(m.label) : m.name]));
  const metricUnits=new Map(selectedMetrics.map(m=>[m.code,m.unit]));
  const chosen=spec.columns.map(code=>({code,name:names.get(code)||code,unit:metricUnits.get(code)||''}));
  const available=all.filter(m=>!spec.columns.includes(m.code)&&`${m.name} ${m.code}`.toLowerCase().includes(search.toLowerCase())).slice(0,100);

  useEffect(()=>{api<Template[]>('/data-export/templates').then(setTemplates).catch(()=>{});
    api<UnitItem[]>('/units').then(setUnits).catch(()=>{});},[]);
  function update(p:Partial<Spec>){setSpec(prev=>({...prev,...p}));setPreview(null);setError('');setNotice('')}
  function toggleAdd(code:string){if(spec.columns.length>=45)return setError('Maksimal 45 kolom');update({columns:[...spec.columns,code]})}
  function move(index:number,step:number){const arr=[...spec.columns],to=index+step;if(to<0||to>=arr.length)return;[arr[index],arr[to]]=[arr[to],arr[index]];update({columns:arr})}
  function remove(code:string){update({columns:spec.columns.filter(v=>v!==code)})}
  function loadTemplate(id:string){setTemplateId(id);const found=templates.find(t=>String(t.id)===id);
    if(found){setSpec(structuredClone(found.spec));setTemplateName(found.name);setPreview(null)}}
  const request={...spec,start,end};
  const valid=!!start&&!!end&&start<=end&&spec.columns.includes('tanggal')&&spec.columns.some(x=>!(x in meta))&&spec.columns.length<=45;
  async function showPreview(){setBusy(true);setError('');try{setPreview(await api<Preview>('/data-export/preview',{method:'POST',body:JSON.stringify(request)}));}
    catch(e){setError(message(e))}finally{setBusy(false)}}
  async function download(){setBusy(true);setError('');try{
    const response=await apiFetch('/api/data-export/download',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(request)});
    if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||`HTTP ${response.status}`)}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=`BerauLoad_${start}_${end}.${spec.format}`;document.body.append(link);link.click();link.remove();
    URL.revokeObjectURL(url);setNotice('File export disiapkan. Periksa folder unduhan browser.');
  }catch(e){setError(message(e))}finally{setBusy(false)}}
  async function saveTemplate(){setBusy(true);setError('');try{
    const saved=await api<Template>('/data-export/templates',{method:'POST',body:JSON.stringify({name:templateName,scope,spec})});
    setTemplates(old=>[...old,saved]);setTemplateId(String(saved.id));setNotice('Template berhasil disimpan.');
  }catch(e){setError(message(e))}finally{setBusy(false)}}
  async function updateTemplate(){const found=templates.find(t=>String(t.id)===templateId);
    if(!found)return;
    setBusy(true);setError('');try{
      const saved=await api<Template>(`/data-export/templates/${found.id}`,{method:'PUT',body:JSON.stringify({
        name:templateName,scope:found.scope,spec,expected_version:found.version})});
      setTemplates(old=>old.map(t=>t.id===saved.id?saved:t));setNotice('Template berhasil diperbarui.');
    }catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function archiveTemplate(){const found=templates.find(t=>String(t.id)===templateId);
    if(!found||!window.confirm('Arsipkan template ini? Data pengukuran tidak berubah.'))return;
    try{await api(`/data-export/templates/${found.id}/archive`,{method:'POST'});setTemplates(old=>old.filter(t=>t.id!==found.id));setTemplateId('');}
    catch(e){setError(message(e))}}

  return <div className="page-space export-builder">
    <div className="page-top"><div><div className="eyebrow">PELAPORAN • DATA CUSTOM</div><h2>Export Data Excel / CSV</h2>
      <p>Pilih data, atur urutan kolom, lihat contoh, lalu unduh. Pengukuran asli tidak diubah.</p></div></div>
    {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice success">{notice}</div>}
    <div className="panel export-section"><h3>1. Sumber & Periode</h3>
      <div className="export-fields"><label>Tanggal mulai<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Tanggal selesai<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label>
        <label>Resolusi<select value={spec.granularity} onChange={e=>{
          const granularity=e.target.value as Grain;
          update({granularity,columns:granularity==='hour'?spec.columns:spec.columns.filter(x=>x!=='jam'&&x!=='status')})}}>
          <option value="hour">Per jam</option><option value="day">Per hari</option><option value="month">Per bulan</option><option value="year">Per tahun</option></select></label>
        <label>Agregasi<select value={spec.aggregation} onChange={e=>update({aggregation:e.target.value as Agg})} disabled={spec.granularity==='hour'}>
          <option value="avg">Rata-rata</option><option value="max">Maksimum</option><option value="min">Minimum</option></select></label>
        <label>Format<select value={spec.format} onChange={e=>update({format:e.target.value as Format})}>
          <option value="xlsx">Excel (.xlsx)</option><option value="csv">CSV (.csv)</option></select></label>
      </div>
      <p className="muted small">Batas per permintaan 10 tahun. Agregasi per parameter, bukan penjumlahan kW menjadi energi. CSV memakai pemisah titik koma (;).</p></div>
    <div className="export-columns">
      <section className="panel export-section"><h3>2. Pilih Kolom</h3><div className="export-search"><Search size={17}/><input placeholder="Cari parameter atau kode" value={search} onChange={e=>setSearch(e.target.value)}/></div>
        <div className="export-available">{available.map(m=><button className="export-add" key={m.code} disabled={spec.granularity!=='hour'&&['jam','status'].includes(m.code)} onClick={()=>toggleAdd(m.code)}><Plus size={15}/><span>{'label' in m ? String(m.label) : m.name}{m.unit?` (${m.unit})`:''}</span></button>)}
        {available.length===0&&<p className="muted small">Tidak ada parameter lain yang cocok.</p>}</div>
        <p className="muted small">Parameter nonaktif tetap tersedia untuk membaca data historis lama.</p>
      </section>
      <section className="panel export-section"><h3>3. Urutan & Judul Kolom ({chosen.length})</h3><p className="muted small">Gunakan panah untuk mengurutkan. Kolom Tanggal wajib ada.</p>
        <div className="export-selected">{chosen.map((c,i)=>{
          const source=units.find(u=>u.code===c.unit);
          const compatible=source?units.filter(u=>u.dimension===source.dimension&&u.active):[];
          return <div className="export-selected-item" key={c.code}>
            <div className="export-selected-top"><b>{i+1}. {c.name}</b><div className="export-move">
              <button title="Naik" disabled={i===0} onClick={()=>move(i,-1)}><ArrowUp size={15}/></button>
              <button title="Turun" disabled={i===chosen.length-1} onClick={()=>move(i,1)}><ArrowDown size={15}/></button>
              <button title="Hapus kolom" disabled={c.code==='tanggal'} onClick={()=>remove(c.code)}><Trash2 size={15}/></button></div></div>
            <input aria-label={`Judul ${c.name}`} placeholder="Judul default" value={spec.headers[c.code]||''}
              onChange={e=>{const next={...spec.headers};if(e.target.value.trim())next[c.code]=e.target.value;else delete next[c.code];update({headers:next})}}/>
            {compatible.length>1&&<label className="export-unit">Satuan export <select value={spec.unit_overrides[c.code]||c.unit}
              onChange={e=>update({unit_overrides:{...spec.unit_overrides,[c.code]:e.target.value}})}>
              {compatible.map(u=><option key={u.code} value={u.code}>{u.code}</option>)}</select></label>}
          </div>})}</div>
      </section>
    </div>
    <section className="panel export-section"><h3>4. Preview & Unduh</h3><div className="export-actions">
      <button className="btn secondary" disabled={busy||!valid} onClick={showPreview}><Eye size={17}/> Preview 10 Baris</button>
      <button className="btn primary" disabled={busy||!valid} onClick={download}><Download size={17}/> {busy?'Memproses...':'Unduh '+spec.format.toUpperCase()}</button></div>
      {preview&&<><SourceStatusSummary status={preview.source_status}/><div className="scroll-table"><table><thead><tr>{preview.headers.map((x,i)=><th key={i}>{x}</th>)}</tr></thead>
        <tbody>{preview.rows.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{v==null?'—':String(v)}</td>)}</tr>)}</tbody></table></div>
        <p className="muted small">{preview.note}</p></>}
    </section>
    <section className="panel export-section"><h3>5. Template Export</h3><div className="export-fields">
      <label>Template tersimpan<select value={templateId} onChange={e=>loadTemplate(e.target.value)}><option value="">Pilih template</option>
        {templates.map(t=><option value={t.id} key={t.id}>{t.name} · {t.scope==='system'?'Bersama':'Pribadi'}</option>)}</select></label>
      <label>Nama template<input value={templateName} onChange={e=>setTemplateName(e.target.value)}/></label>
      <label>Jenis<select value={scope} onChange={e=>setScope(e.target.value)}><option value="personal">Pribadi</option>
        {role==='admin'&&<option value="system">Bersama (Admin)</option>}</select></label></div>
      <div className="export-actions"><button className="btn secondary" disabled={busy||!valid||templateName.trim().length<3} onClick={saveTemplate}><Save size={16}/> Simpan sebagai Template Baru</button>
        <button className="btn secondary" disabled={busy||!valid||!templateId||templates.find(t=>String(t.id)===templateId)?.scope==='system'&&role!=='admin'} onClick={updateTemplate}><Save size={16}/> Perbarui Template Terpilih</button>
        <button className="btn secondary" disabled={!templateId||templates.find(t=>String(t.id)===templateId)?.scope==='system'&&role!=='admin'} onClick={archiveTemplate}><Trash2 size={16}/> Arsipkan Template</button></div>
    </section>
  </div>;
}
