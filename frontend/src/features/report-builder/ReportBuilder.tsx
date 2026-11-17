import {useEffect,useMemo,useState} from 'react';
import {Archive,ArrowDown,ArrowUp,Copy,Download,Eye,FileSpreadsheet,FileText,Plus,Save,Trash2} from 'lucide-react';
import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,downloadApi,isoWita,num,qs,type Catalog,type User} from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import {SourceStatusSummary} from '../unit-references/SourceStatus';
import UnitMetricOptions from '../unit-references/UnitMetricOptions';
import {newBlock,type ReportBlock,type ReportKind,type ReportResult,type ReportTemplate} from './types';
import './report-builder.css';
import {useBranding} from '../branding/BrandingContext';
import {safeBrandSlug} from '../branding/branding.mjs';

const kinds:[ReportKind,string][]=[['heading','Judul Bagian'],['text','Paragraf'],['stat','KPI'],['chart','Grafik'],['table','Tabel']];
const errorText=(e:unknown)=>e instanceof Error?e.message:String(e);
const seed=()=>[newBlock('heading'),newBlock('stat'),newBlock('chart')];
const initialDate=isoWita();
const templateNew=()=>({id:0,name:'Laporan Operasional Baru',description:'',scope:'personal' as const,
  owner_id:0,blocks:seed(),version:0,archived:false});

function ReportBlockPreview({block}:{block:ReportResult['blocks'][number]}){
  if(block.kind==='heading')return <h3>{block.title}</h3>;
  if(block.kind==='text')return <section><h4>{block.title}</h4><p className="report-note-text">{block.text||'—'}</p></section>;
  if(block.kind==='stat')return <section><h4>{block.title}</h4><strong className="report-stat">{num(block.value,2)} {block.unit}</strong>
    <small>{block.count||0} pembacaan valid</small></section>;
  if(block.kind==='table')return <section><h4>{block.title}</h4><div className="scroll-table"><table><thead><tr><th>Periode</th>
    {block.metric_codes.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{(block.rows||[]).slice(0,30).map(r=><tr key={r.period}>
    <td>{r.period}</td>{block.metric_codes.map(c=><td key={c}>{typeof r[c]==='number'?num(Number(r[c]),2):'—'}</td>)}</tr>)}
    </tbody></table></div><small>Pratinjau maksimal 30 baris; ekspor mengikuti periode.</small></section>;
  const series=block.metric_codes;
  return <section><h4>{block.title}</h4>{block.rows?.some(r=>series.some(c=>typeof r[c]==='number'))?<div className="report-chart">
    <ResponsiveContainer width="100%" height="100%"><LineChart data={block.rows}>
      <CartesianGrid vertical={false} strokeDasharray="3 4"/><XAxis dataKey="period" tick={{fontSize:10}} minTickGap={20}/>
      <YAxis width={57} tick={{fontSize:10}}/><Tooltip/><Legend/>
      {series.map((c,i)=><Line key={c} dataKey={c} name={c} stroke={['#087f8c','#e78538'][i]}
        dot={false} connectNulls={false} isAnimationActive={false}/>)}
    </LineChart></ResponsiveContainer></div>:<p className="muted">Belum ada data pada periode ini.</p>}</section>;
}

export default function ReportBuilder({catalog,user}:{catalog:Catalog;user:User}){
 const {branding}=useBranding();
  const [templates,setTemplates]=useState<ReportTemplate[]>([]);
  const [draft,setDraft]=useState<ReportTemplate|null>(null);
  const [dirty,setDirty]=useState(false);
  const [preview,setPreview]=useState<ReportResult|null>(null);
  const [start,setStart]=useState(initialDate.slice(0,8)+'01');
  const [end,setEnd]=useState(initialDate);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const writable=draft?.scope==='personal'?draft.owner_id===user.id||draft.id===0:user.role==='admin';
  const references=useUnitMetricReferences();
  const metrics=useMemo(()=>metricsForSelection(references,catalog.metrics).filter(m=>m.code!=='daya_mampu_sistem_kw'),[catalog,references]);

  async function load(preferred?:number){
    const items=await api<ReportTemplate[]>('/report-builder');
    setTemplates(items);
    if(preferred){const saved=items.find(x=>x.id===preferred);setDraft(saved?structuredClone(saved):null);}
    else if(!draft){setDraft(items[0]?structuredClone(items[0]):templateNew());}
    setDirty(false);
  }
  useEffect(()=>{load().catch(e=>setError(errorText(e)));},[]);
  function patch(change:Partial<ReportTemplate>){setDraft(p=>p?{...p,...change}:null);setDirty(true);setPreview(null);}
  function changeBlock(id:string,change:Partial<ReportBlock>){if(!draft)return;
    patch({blocks:draft.blocks.map(b=>b.id===id?{...b,...change}:b)});
  }
  function move(index:number,delta:number){if(!draft)return;const next=[...draft.blocks];
    const other=index+delta;if(other<0||other>=next.length)return;
    [next[index],next[other]]=[next[other],next[index]];patch({blocks:next});
  }
  function selectTemplate(value:number){if(dirty&&!window.confirm('Abaikan perubahan laporan yang belum disimpan?'))return;
    const saved=templates.find(t=>t.id===value);setDraft(saved?structuredClone(saved):templateNew());
    setDirty(false);setPreview(null);setError('');
  }
  async function save(){if(!draft||!writable)return;setBusy(true);setError('');
    const data={name:draft.name,description:draft.description,scope:draft.scope,blocks:draft.blocks};
    try{const saved=await api<ReportTemplate>(draft.id?`/report-builder/${draft.id}`:'/report-builder',{
      method:draft.id?'PUT':'POST',body:JSON.stringify(draft.id?{...data,expected_version:draft.version}:data)});
      await load(saved.id);setNotice('Template laporan berhasil disimpan.');
    }catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  async function previewReport(){if(!draft)return;setBusy(true);setError('');
    try{const result=await api<ReportResult>('/report-builder/preview',{method:'POST',body:JSON.stringify({
      blocks:draft.blocks,start,end})});setPreview(result);
    }catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  async function action(type:'duplicate'|'archive'){
    if(!draft?.id||!window.confirm(type==='archive'?'Arsipkan template ini?':'Duplikasi sebagai template pribadi?'))return;
    setBusy(true);setError('');try{const result=await api<ReportTemplate|{ok:boolean}>(`/report-builder/${draft.id}/${type}`,{method:'POST'});
      setDraft(null);setPreview(null);setDirty(false);
      const items=await api<ReportTemplate[]>('/report-builder');setTemplates(items);
      setDraft(items.find(t=>'id' in result&&t.id===result.id)||items[0]||templateNew());
      setNotice('Tindakan berhasil.');
    }catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  const download=async(format:'pdf'|'xlsx')=>{
    if(!draft?.id||dirty){setError('Simpan template terlebih dahulu sebelum ekspor.');return;}
    try{await downloadApi(`/report-builder/${draft.id}/download?${qs({start,end,format})}`,`${safeBrandSlug(branding.app_short_name)}_Laporan_${start}_${end}.${format}`)}
    catch(e){setError(errorText(e))}
  };
  return <div className="report-builder page-space">
    <div className="page-top"><div><div className="eyebrow">LAPORAN MANAJEMEN • KUSTOM</div><h2>Report Builder</h2>
      <p>Susun laporan manajemen tanpa Python, SQL, atau mengubah data historis.</p></div></div>
    {error&&<div className="notice error" role="alert">{error}</div>}
    {notice&&<div className="notice success">{notice}</div>}
    <div className="report-top panel">
      <label>Template laporan<select value={draft?.id||0} onChange={e=>selectTemplate(Number(e.target.value))}>
        <option value={0}>Laporan Baru (belum disimpan)</option>{templates.map(x=><option key={x.id} value={x.id}>{x.name} ({x.scope==='system'?'Sistem':'Pribadi'})</option>)}
      </select></label>
      <button className="btn secondary" onClick={()=>{if(!dirty||window.confirm('Buat laporan baru?')){setDraft(templateNew());setDirty(false);setPreview(null)}}}><Plus size={16}/> Baru</button>
      <label>Mulai<input type="date" value={start} onChange={e=>{setStart(e.target.value);setPreview(null)}}/></label>
      <label>Sampai<input type="date" value={end} onChange={e=>{setEnd(e.target.value);setPreview(null)}}/></label>
    </div>
    {draft&&<><div className="report-toolbar">
      <div className="report-title-fields"><label>Nama laporan<input disabled={!writable} value={draft.name} onChange={e=>patch({name:e.target.value})}/></label>
        <label>Deskripsi<input disabled={!writable} value={draft.description} onChange={e=>patch({description:e.target.value})}/></label>
        {draft.id===0&&user.role==='admin'&&<label>Jenis template<select value={draft.scope} onChange={e=>patch({scope:e.target.value as 'system'|'personal'})}>
          <option value="personal">Pribadi</option><option value="system">Sistem (semua pengguna)</option></select></label>}</div>
      <div className="report-actions"><button disabled={!writable||busy} className="btn primary" onClick={save}><Save size={16}/> Simpan</button>
        <button className="btn secondary" onClick={()=>{if(draft.id)selectTemplate(draft.id);else{setDraft(templateNew());setDirty(false)}}}>Batal</button>
        <button className="btn secondary" disabled={busy} onClick={previewReport}><Eye size={16}/> Pratinjau</button></div></div>
      <div className="report-workspace">
        <div className="report-editor panel"><h3>Susunan laporan</h3><p className="muted small">Atur bagian laporan dengan tombol naik/turun.</p>
          {draft.blocks.map((block,i)=><div className="report-block-form" key={block.id}>
            <div className="report-block-head"><strong>{i+1}. {kinds.find(k=>k[0]===block.kind)?.[1]}</strong>
              {writable&&<div><button title="Naik" disabled={!i} onClick={()=>move(i,-1)}><ArrowUp size={15}/></button>
              <button title="Turun" disabled={i===draft.blocks.length-1} onClick={()=>move(i,1)}><ArrowDown size={15}/></button>
              <button title="Hapus bagian" onClick={()=>patch({blocks:draft.blocks.filter(b=>b.id!==block.id)})}><Trash2 size={15}/></button></div>}</div>
            <label>Judul<input disabled={!writable} value={block.title} onChange={e=>changeBlock(block.id,{title:e.target.value})}/></label>
            {block.kind==='text'&&<label>Isi paragraf<textarea disabled={!writable} rows={4} value={block.text}
              onChange={e=>changeBlock(block.id,{text:e.target.value})}/></label>}
            {!['heading','text'].includes(block.kind)&&<><label>Parameter<select disabled={!writable} value={block.metric_codes[0]||''}
              onChange={e=>changeBlock(block.id,{metric_codes:e.target.value?[e.target.value]:[]})}>
              <option value="">Pilih parameter</option><UnitMetricOptions metrics={metrics}/></select></label>
              {['chart','table'].includes(block.kind)&&<label>Parameter kedua (opsional)<select disabled={!writable}
                value={block.metric_codes[1]||''} onChange={e=>changeBlock(block.id,{metric_codes:block.metric_codes.slice(0,1).concat(e.target.value?[e.target.value]:[])})}>
                  <option value="">Tanpa parameter kedua</option>{metrics.filter(m=>m.code!==block.metric_codes[0]&&m.unit===metrics.find(x=>x.code===block.metric_codes[0])?.unit)
                  .map(m=><option key={m.code} value={m.code}>{'label' in m ? String(m.label):m.name}</option>)}</select></label>}
              <div className="report-inline"><label>Metode<select disabled={!writable} value={block.aggregation}
                onChange={e=>changeBlock(block.id,{aggregation:e.target.value as ReportBlock['aggregation']})}>
                <option value="avg">Rata-rata</option><option value="peak">Maksimum</option><option value="min">Minimum</option></select></label>
                {['chart','table'].includes(block.kind)&&<label>Resolusi<select disabled={!writable} value={block.granularity}
                  onChange={e=>changeBlock(block.id,{granularity:e.target.value as ReportBlock['granularity']})}>
                  <option value="hour">Jam</option><option value="day">Hari</option><option value="month">Bulan</option></select></label>}</div>
            </>}</div>)}
          {writable&&<div className="report-add">{kinds.map(([kind,label])=><button className="btn secondary sm" key={kind}
            disabled={draft.blocks.length>=16} onClick={()=>patch({blocks:[...draft.blocks,newBlock(kind)]})}><Plus size={13}/>{label}</button>)}</div>}
        </div>
        <div className="report-preview panel"><h3>Pratinjau laporan</h3>
          <SourceStatusSummary status={preview?.source_status}/>
          {!preview?<p className="muted">Tekan Pratinjau untuk melihat laporan dengan data historis sebenarnya.</p>:
          <><div className="report-paper"><h2>{draft.name}</h2><p>{draft.description}</p><small>{preview.start} – {preview.end} • WITA</small>
            {preview.blocks.map(b=><ReportBlockPreview key={b.id} block={b}/>)}</div></>}
          <div className="report-actions"><button className="btn secondary" disabled={!draft.id||dirty} onClick={()=>download('pdf')}>
            <FileText size={16}/> PDF</button><button className="btn secondary" disabled={!draft.id||dirty} onClick={()=>download('xlsx')}>
            <FileSpreadsheet size={16}/> Excel</button></div>
          <p className="muted small">CSV mentah dengan kolom bebas tersedia di menu Export Data Excel/CSV.</p>
        </div>
      </div>
      <div className="report-bottom-actions">{draft.id>0&&<><button className="btn secondary" onClick={()=>action('duplicate')}><Copy size={15}/> Duplikasi</button>
        {writable&&<button className="btn secondary" onClick={()=>action('archive')}><Archive size={15}/> Arsipkan</button>}</>}
      </div>
    </>}
  </div>;
}
