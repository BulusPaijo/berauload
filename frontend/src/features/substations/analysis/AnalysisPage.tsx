import {useCallback,useEffect,useMemo,useState} from 'react';
import type {DragEvent} from 'react';
import {api,apiFetch,activeUnitId,csrf,downloadApi} from '../../../api';
import {applyView,chips,designColumns,direction,findingColumns,fromQuery,serializeView,toQuery} from './helpers.mjs';
import type {AnalysisDefinitions,AnalysisRow,RowResponse,SavedView,Summary} from './types';
import ChartDashboard from './ChartDashboard';
import {isNumericColumn,renderCell} from './AnalysisCells';
import {readDensity,saveDensity} from './chartHelpers.mjs';
import GarduDetail from '../detail/GarduDetail';
import {canWrite,useScope} from '../scope';
import './analysis.css';
import './analysis-9d3.css';
import FindingPicker from '../ui/FindingPicker';

type Filter=Record<string,string|string[]> & {findings:string[]};
const attributes:Record<string,string>={code:'Gardu',name:'Nama / alamat',feeder:'Penyulang',power_kva:'kVA',brand:'Merk',address:'Alamat',
 measured_on:'Diukur',session:'Sesi',state:'Verifikasi',status:'Status ukur',reference:'Beban tertinggi',category:'Kondisi',findings:'Temuan',followup:'Tindak lanjut'};
const message=(e:unknown)=>e instanceof Error?e.message:String(e);
const refreshURL=(filter:Filter)=>{const q=new URLSearchParams(toQuery(filter));q.set('gardu_tab','analysis');window.history.replaceState(null,'',window.location.pathname+'?'+q);};
type Props={admin:boolean;userId:number;canInput:boolean;onNavigate:(tab:string,stationId?:number|string)=>void};
export default function AnalysisPage({admin,userId,canInput,onNavigate}:Props){
 const [defs,setDefs]=useState<AnalysisDefinitions|null>(null);
 const [filter,setFilter]=useState<Filter>(()=>fromQuery(window.location.search));
 const [rows,setRows]=useState<RowResponse|null>(null),[summary,setSummary]=useState<Summary|null>(null);
 const [views,setViews]=useState<SavedView[]>([]),[columns,setColumns]=useState<string[]|null>(null);
 const [density,setDensity]=useState<'compact'|'comfortable'>(()=>readDensity(localStorage,userId));
 const [viewDialog,setViewDialog]=useState<{shared:boolean;asDefault:boolean}|null>(null),[viewName,setViewName]=useState('');
 const [selected,setSelected]=useState<number[]>([]),[open,setOpen]=useState<AnalysisRow|null>(null);
 const [columnPanel,setColumnPanel]=useState(false),[reload,setReload]=useState(0);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const unit=activeUnitId();
 const scope=useScope();
 const query=useMemo(()=>toQuery(filter),[filter]);
 const set=useCallback((value:Partial<Filter>)=>setFilter(f=>({...f,...value,page:'1'})),[]);
 const reloadViews=()=>api<SavedView[]>('/substations/analysis/views').then(setViews).catch(e=>setError(message(e)));
 useEffect(()=>{Promise.all([api<AnalysisDefinitions>('/substations/analysis/definitions'),api<SavedView[]>('/substations/analysis/views')])
  .then(([d,found])=>{setDefs(d);setViews(found);
   const personal=found.find(v=>v.is_default&&!v.shared);
   if(personal&&![...new URLSearchParams(window.location.search).keys()].some(k=>k!=='gardu_tab')){const r=applyView(personal,d);
    setFilter(r as Filter);if(Array.isArray(r.columns))setColumns(r.columns as string[]);
    if(personal.warnings.length)setNotice('Definisi yang diarsipkan dilewati: '+personal.warnings.join(', '));}
  }).catch(e=>setError(message(e)));},[unit]);
 useEffect(()=>{refreshURL(filter);let valid=true;setBusy(true);
  Promise.all([api<RowResponse>('/substations/analysis/rows?'+query),api<Summary>('/substations/analysis/summary?'+query)])
   .then(([r,t])=>{if(valid){setRows(r);setSummary(t);setError('');setSelected([]);}})
   .catch(e=>{if(valid)setError(message(e))}).finally(()=>{if(valid)setBusy(false)});
  return()=>{valid=false};},[query,unit,reload]);
 useEffect(()=>{if(!open)return;const k=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(null)};window.addEventListener('keydown',k);return()=>window.removeEventListener('keydown',k)},[open]);
 const shown=columns??designColumns(defs);
 const marks=useMemo(()=>findingColumns(defs?.rules??[]),[defs]);
 const refUnit=defs?.columns.find(c=>c.code===defs.reference_code)?.unit??'';
 const maxRef=refUnit==='%'?Math.max(100,...(rows?.items??[]).map(r=>r.reference??0)):Math.max(1,...(rows?.items??[]).map(r=>Math.abs(r.reference??0)));
 const choices=useMemo(()=>[...Object.entries(attributes).map(([code,name])=>({code,name})),
  ...(defs?.sessions??[]).map(s=>({code:'sesi:'+s.code,name:s.name})),
  ...(defs?.columns??[]).map(({code,name})=>({code,name})),...(defs?.fields??[]).map(({code,name})=>({code:'extra_'+code,name}))],[defs]);
 const nameFor=(code:string)=>choices.find(v=>v.code===code)?.name??code;
 const sortKey=(code:string)=>code==='reference'?defs?.reference_code??'code':code.startsWith('sesi:')?defs?.reference_code??'code':code;
 const sortable=(code:string)=>!['findings','category','followup'].includes(code);
 const ctx={defs,maxRef,refUnit,marks,onOpen:(r:AnalysisRow)=>setOpen(r)};
 const rowKey=(r:AnalysisRow)=>r.measurement_id??-r.id;
 const pickedRows=(rows?.items??[]).filter(r=>selected.includes(rowKey(r)));
 function selectView(id:number){const view=views.find(v=>v.id===id);if(!view)return;const r=applyView(view,defs??undefined);
  setFilter(r as Filter);setColumns(Array.isArray(r.columns)?r.columns as string[]:null);
  setNotice(view.warnings.length?'Beberapa definisi pada tampilan ini telah diarsipkan: '+view.warnings.join(', '):'Tampilan dimuat.');}
 async function saveView(shared=false,asDefault=false){const name=viewName.trim();if(!name)return;
  try{await api('/substations/analysis/views',{method:'POST',body:JSON.stringify({name,shared,is_default:asDefault,layout:serializeView(filter,shown,{})})});
   await reloadViews();setViewDialog(null);setViewName('');setNotice('Tampilan disimpan.');}catch(e){setError(message(e))}}
 async function exportRows(format:'csv'|'xlsx',chosen=false){const q=new URLSearchParams(query);q.set('format',format);q.set('columns',shown.join(','));
  if(chosen){if(!selected.length)return;q.set('ids',selected.join(','));}
  try{await downloadApi('/substations/analysis/export?'+q,`Analisa_Gardu.${format}`)}catch(e){setError(message(e))}}
 async function report(format:'pdf'|'xlsx'){setNotice('Menyiapkan laporan…');
  try{await downloadApi(`/substations/monitoring/report?format=${format}&${query}`,`Laporan_Gardu.${format}`);setNotice('Laporan diunduh.')}catch(e){setError(message(e))}}
 async function worksheet(){const ids=[...new Set(pickedRows.map(r=>r.id))];if(!ids.length)return;
  try{const r=await apiFetch('/api/substations/monitoring/worksheet',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({ids,format:'pdf'})});
   if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||`HTTP ${r.status}`);
   const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='Lembar_Kerja_Gardu.pdf';document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);}
  catch(e){setError(message(e))}}
 function dropColumn(e:DragEvent<HTMLButtonElement>,target:string){e.preventDefault();const src=e.dataTransfer.getData('text/plain'),a=shown.indexOf(src),b=shown.indexOf(target);
  if(a<0||b<0)return;const next=shown.slice();next.splice(a,1);next.splice(b,0,src);setColumns(next);}
 const advancedCount=[filter.state,filter.min_kva,filter.max_kva,filter.numeric_code,filter.status,filter.unit_id].filter(Boolean).length;
 const unitName=defs?.units.find(u=>u.id===unit)?.name;
 return <div className="analysis-page an9">
  <header className="an-head"><div><div className="substation-kicker">PENGUKURAN GARDU · ANALISA</div><h2>Analisa &amp; Tindak Lanjut</h2>
   <p>{unitName?unitName+' · ':''}{filter.mode==='terakhir'?'pengukuran terakhir tiap gardu':filter.mode==='periode'?'terbaru dalam periode':'semua pengukuran'} · ambang diatur admin</p></div>
   <div className="an-actions"><button className="btn secondary" onClick={()=>onNavigate('map')}>Peta</button><button className="btn secondary" onClick={()=>setColumnPanel(v=>!v)}>Atur kolom</button>
    <select aria-label="Tampilan tersimpan" value="" onChange={e=>selectView(Number(e.target.value))}><option value="">Tampilan…</option>{views.map(v=><option key={v.id} value={v.id}>{v.shared?'Tim · ':''}{v.name}{v.is_default?' (bawaan)':''}</option>)}</select>
    <details className="analysis-menu"><summary className="btn primary">Unduh ▾</summary><div className="analysis-menu-pop" role="menu">
     <button role="menuitem" onClick={()=>void exportRows('xlsx')}>Tabel ini (Excel)</button><button role="menuitem" onClick={()=>void exportRows('csv')}>Tabel ini (CSV)</button>
     <button role="menuitem" onClick={()=>void report('pdf')}>Laporan PDF<small>Ringkasan, daftar per kondisi, tindak lanjut</small></button><button role="menuitem" onClick={()=>void report('xlsx')}>Laporan Excel</button>
     <button role="menuitem" onClick={()=>onNavigate('export')}><b>Export Data Gardu…</b><small>Pilih sendiri kolom dan bentuk data</small></button></div></details>
    <details className="analysis-menu"><summary className="btn secondary" aria-label="Menu tampilan">⋯</summary><div className="analysis-menu-pop" role="menu">
     <button role="menuitem" onClick={()=>{setViewDialog({shared:false,asDefault:false});setViewName('')}}>Simpan tampilan</button>
     <button role="menuitem" onClick={()=>{setViewDialog({shared:false,asDefault:true});setViewName('')}}>Jadikan bawaan saya</button>
     {admin&&<button role="menuitem" onClick={()=>{setViewDialog({shared:true,asDefault:false});setViewName('')}}>Bagikan ke tim</button>}
     <label className="an-density">Kepadatan<select value={density} onChange={e=>{const v=e.target.value as 'compact'|'comfortable';setDensity(v);saveDensity(localStorage,userId,v)}}><option value="comfortable">Nyaman</option><option value="compact">Padat</option></select></label></div></details></div></header>
  {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div role="status" className="notice info">{notice}</div>}
  {defs&&<section className="an-top">
   <ChartDashboard fixed query={query} definitions={defs} chart="feeder" onChartChange={()=>{}} onPick={()=>{}}/>
   <ChartDashboard fixed query={query} definitions={defs} chart="scatter" onChartChange={()=>{}} onPick={id=>{const r=rows?.items.find(x=>x.id===id);if(r)setOpen(r);else set({text:''})}}/>
   <div className="an-attn"><h3>Perlu perhatian</h3>
    {(summary?.categories??[]).slice().reverse().map(c=><button key={c.code} className={filter.category===c.code?'on':''} onClick={()=>set({category:filter.category===c.code?'':c.code})}><span>{c.name}</span><b style={{color:c.color}}>{c.count} gardu</b></button>)}
    {(summary?.findings??[]).filter(f=>f.count>0).map(f=><button key={f.code} className={filter.findings.includes(f.code)?'on':''} onClick={()=>set({findings:filter.findings.includes(f.code)?filter.findings.filter(x=>x!==f.code):[...filter.findings,f.code]})}><span>{f.name}</span><b style={{color:f.color}}>{f.count} gardu</b></button>)}
    <button className={filter.status==='belum'?'on':''} onClick={()=>set({status:filter.status==='belum'?'':'belum'})}><span>Belum pernah diukur</span><b>{summary?.unassessed??0}*</b></button>
    <p>Klik baris untuk menyaring tabel. *tidak dapat dinilai</p></div>
  </section>}
  <section className="an-filters">
   <input aria-label="Cari gardu" placeholder="Cari gardu, alamat, merk" value={String(filter.text||'')} onChange={e=>set({text:e.target.value})}/>
   <select aria-label="Mode data" value={String(filter.mode)} onChange={e=>set({mode:e.target.value})}><option value="terakhir">Pengukuran terakhir</option><option value="periode">Periode</option><option value="semua">Semua pengukuran</option></select>
   {filter.mode!=='terakhir'&&<><input aria-label="Dari tanggal" type="date" value={String(filter.start||'')} onChange={e=>set({start:e.target.value})}/><input aria-label="Sampai tanggal" type="date" value={String(filter.end||'')} onChange={e=>set({end:e.target.value})}/></>}
   <select aria-label="Sesi" value={String(filter.session)} onChange={e=>set({session:e.target.value})}><option value="tertinggi">Tertinggi antar sesi</option>{defs?.sessions.map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select>
   <select aria-label="Penyulang" value={String(filter.feeder_id||'')} onChange={e=>set({feeder_id:e.target.value})}><option value="">Semua penyulang</option>{defs?.feeders.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select>
   <div className="an-chips">{chips(defs?.rules??[]).map(r=>{const on=filter.category===r.code||filter.findings.includes(r.code);
    return <button key={r.code} aria-pressed={on} className={on?'on':''} onClick={()=>r.kind==='category'?set({category:filter.category===r.code?'':r.code}):set({findings:on?filter.findings.filter(v=>v!==r.code):[...filter.findings,r.code]})}>{r.name}</button>})}
    <button aria-pressed={filter.status==='belum'} className={filter.status==='belum'?'on':''} onClick={()=>set({status:filter.status==='belum'?'':'belum'})}>Belum diukur</button></div>
   <span className="an-count">{rows?.total??0} dari {summary?.total??0} {filter.mode==='semua'?'pengukuran':'gardu'}</span>
  </section>
  <details className="analysis-advanced" open={advancedCount>0||undefined}><summary>Filter lanjutan{advancedCount>0&&<span className="analysis-badge">{advancedCount} aktif</span>}</summary>
   <div className="an-adv">
    <select aria-label="Unit" value={String(filter.unit_id||'')} onChange={e=>set({unit_id:e.target.value})}><option value="">Semua unit yang berhak</option>{defs?.units.map(u=><option key={u.id} value={u.id}>{u.level.toUpperCase()} · {u.name}</option>)}</select>
    <select aria-label="Status ukur" value={String(filter.status||'')} onChange={e=>set({status:e.target.value})}><option value="">Semua status ukur</option><option value="baru">Terukur</option><option value="lama">Lebih dari batas hari</option><option value="belum">Belum pernah</option></select>
    <select aria-label="Verifikasi" value={String(filter.state||'')} onChange={e=>set({state:e.target.value})}><option value="">Draft &amp; verified</option><option value="draft">Draft</option><option value="verified">Verified</option></select>
    <input aria-label="kVA minimum" type="number" placeholder="kVA min" value={String(filter.min_kva||'')} onChange={e=>set({min_kva:e.target.value})}/>
    <input aria-label="kVA maksimum" type="number" placeholder="kVA maks" value={String(filter.max_kva||'')} onChange={e=>set({max_kva:e.target.value})}/>
    <select aria-label="Kolom hitung" value={String(filter.numeric_code||'')} onChange={e=>set({numeric_code:e.target.value})}><option value="">Syarat angka: tanpa</option>{defs?.columns.map(c=><option key={c.code} value={c.code}>{c.name}</option>)}</select>
    {filter.numeric_code&&<select aria-label="Operator" value={String(filter.numeric_op||'')} onChange={e=>set({numeric_op:e.target.value})}><option value="">Operator</option><option value="gte">≥</option><option value="lte">≤</option><option value="antara">Antara</option><option value="kosong">Kosong</option><option value="ada">Tidak kosong</option></select>}
    {!['','ada','kosong'].includes(String(filter.numeric_op||''))&&<input aria-label="Nilai pembanding" type="number" value={String(filter.numeric_min??'')} onChange={e=>set({numeric_min:e.target.value})}/>}
    {filter.numeric_op==='antara'&&<input aria-label="Nilai atas" type="number" value={String(filter.numeric_max??'')} onChange={e=>set({numeric_max:e.target.value})}/>}
    <button className="btn secondary sm" onClick={()=>setFilter({...fromQuery('')})}>Hapus semua filter</button>
    <FindingPicker findings={(defs?.rules??[]).filter(r=>r.kind==='finding')} picked={filter.findings} mode={String(filter.finding_mode||'any')} onChange={(findings,finding_mode)=>set({findings,finding_mode})}/></div></details>
  {columnPanel&&<section className="analysis-columns"><h3>Atur kolom · seret untuk mengurutkan</h3><div>{choices.map(c=><button key={c.code} draggable={shown.includes(c.code)} onDragStart={e=>e.dataTransfer.setData('text/plain',c.code)} onDragOver={e=>e.preventDefault()} onDrop={e=>dropColumn(e,c.code)} className={shown.includes(c.code)?'selected':''} onClick={()=>setColumns(shown.includes(c.code)?shown.filter(x=>x!==c.code):[...shown,c.code])}>{c.name}</button>)}</div><button className="btn secondary sm" onClick={()=>setColumns(null)}>Kembalikan susunan bawaan</button></section>}
  <section className={'analysis-table-wrap an-table density-'+density}><div className="analysis-table-scroll"><table><thead><tr>
   <th><input aria-label="Pilih semua pada halaman" type="checkbox" checked={!!rows?.items.length&&rows.items.every(r=>selected.includes(rowKey(r)))} onChange={e=>setSelected(e.target.checked?(rows?.items??[]).map(rowKey):[])}/></th>
   {shown.map(code=><th key={code} className={isNumericColumn(code,defs)?'num':''} aria-sort={filter.sort===sortKey(code)&&sortable(code)?(filter.desc==='true'?'descending':'ascending'):'none'}>
    {sortable(code)?<button className="analysis-sort" onClick={()=>setFilter(f=>({...f,...direction(f,sortKey(code))}))}>{nameFor(code)}<span className="analysis-sort-mark" aria-hidden="true">{filter.sort===sortKey(code)?(filter.desc==='true'?'▼':'▲'):''}</span></button>:nameFor(code)}</th>)}</tr></thead>
   <tbody>{rows?.items.map(row=><tr key={rowKey(row)} tabIndex={0} className={'analysis-row'+(open?.id===row.id?' is-open':'')} onKeyDown={e=>{if(e.key==='Enter')setOpen(row)}} onClick={e=>{if((e.target as HTMLElement).closest('input,button,a'))return;setOpen(row)}}>
    <td><input type="checkbox" aria-label={'Pilih '+row.code} checked={selected.includes(rowKey(row))} onChange={e=>setSelected(v=>e.target.checked?[...v,rowKey(row)]:v.filter(x=>x!==rowKey(row)))}/></td>
    {shown.map(code=><td key={code} className={isNumericColumn(code,defs)?'num':''}>{renderCell(row,code,ctx)}{code==='code'&&row.stale_result&&<small className="analysis-stale">Versi lama</small>}</td>)}</tr>)}
   {!rows?.items.length&&<tr><td colSpan={shown.length+1}><div className="an-empty"><b>{busy?'Memuat…':'Tidak ada gardu yang cocok'}</b>{!busy&&<button className="link-btn" onClick={()=>setFilter({...fromQuery('')})}>Hapus semua filter</button>}</div></td></tr>}</tbody></table></div>
   <footer className="analysis-footer an-foot"><span>× = di luar batas temuan · klik judul kolom untuk mengurutkan · centang baris untuk ekspor atau lembar kerja</span>
    <span>{selected.length>0&&<><b>{selected.length} dipilih</b><button className="btn secondary sm" onClick={()=>void worksheet()}>Lembar kerja PDF</button><button className="btn secondary sm" onClick={()=>void exportRows('xlsx',true)}>Ekspor dipilih</button></>}
     <span>Halaman {filter.page} dari {Math.max(1,Math.ceil((rows?.total??0)/Number(filter.page_size||50)))}</span>
     <button className="btn secondary sm" disabled={Number(filter.page)<=1} onClick={()=>setFilter(f=>({...f,page:String(Math.max(1,Number(f.page)-1))}))}>‹</button><button className="btn secondary sm" disabled={!rows||Number(filter.page)*Number(filter.page_size)>=rows.total} onClick={()=>setFilter(f=>({...f,page:String(Number(f.page)+1)}))}>›</button></span></footer></section>
  {viewDialog&&<div className="substation-modal-backdrop" role="presentation"><div className="substation-modal" role="dialog" aria-modal="true" aria-label="Simpan tampilan"><h3>Nama tampilan</h3><label>Nama<input autoFocus maxLength={150} value={viewName} onChange={e=>setViewName(e.target.value)}/></label><div className="substation-dialog-actions"><button className="btn secondary" onClick={()=>setViewDialog(null)}>Batal</button><button className="btn primary" disabled={!viewName.trim()} onClick={()=>void saveView(viewDialog.shared,viewDialog.asDefault)}>Simpan</button></div></div></div>}
  {open&&<><div className="analysis-drawer-backdrop" onClick={()=>setOpen(null)}/><aside className="an-drawer" role="dialog" aria-label={'Rincian '+open.code}>
   <GarduDetail station={{...open,findings:open.findings}} canInput={canInput&&canWrite(scope,open.unit_id)} canFollow={canInput&&canWrite(scope,open.unit_id)} onClose={()=>setOpen(null)}
    onNavigate={(tab,id)=>{setOpen(null);onNavigate(tab,id)}} onChange={()=>setReload(x=>x+1)}/></aside></>}
 </div>;
}
