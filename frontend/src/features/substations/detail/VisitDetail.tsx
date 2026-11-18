import {useState} from 'react';
import {downloadApi,num} from '../../../api';
import type {Definitions,Visit} from '../types';
import type {CalcResults} from '../formulas/types';
import ResultPanel from '../formulas/ResultPanel';
import Drawer from '../ui/Drawer';
import type {Changed,HistoryEntry,TCell} from './visitTable.mjs';
import {fmtValue,historyView,stateLabel,visitTable,whenLabel} from './visitTable.mjs';
import './visit-detail.css';

export type VisitHeader={substation_code:string|null;substation_name:string|null;line_labels:string[];unit_code:string|null;
 unit_name:string|null;unit_level:string|null;feeder_code:string|null;feeder_name:string|null;session_name:string;
 created_by_name:string|null;updated_by_name:string|null;verified_by_name:string|null};
export type VisitDetailData={measurement:Visit&{snapshot_power_kva:number;snapshot_line_count:number;updated_at:string;verified_at:string|null};
 header:VisitHeader;calculated:CalcResults|null;history:HistoryEntry[];changed_cells:Changed[];audit:unknown[]};
type Tab='table'|'history'|'raw';
const LIMIT=6;

/** 9d-5: measurement detail in three tabs — Excel-like values, plain-language history, raw JSON (hidden). */
export default function VisitDetail({data,defs,onClose}:{data:VisitDetailData;defs:Definitions;onClose:()=>void}){
 const [tab,setTab]=useState<Tab>('table'),[open,setOpen]=useState<number[]>([]),[raw,setRaw]=useState(false),[err,setErr]=useState('');
 const m=data.measurement,h=data.header;
 const flagName=(f:string)=>defs.flags.find(x=>x.code===f)?.name??f;
 const labels=h.line_labels??[];
 const t=visitTable(defs.params,m.values,m.snapshot_line_count,labels,data.changed_cells);
 const story=historyView(data.history,flagName,labels);
 const tip=(c:TCell)=>c.changed?`Sebelumnya: ${c.beforeFlag?flagName(c.beforeFlag):c.before==null?'kosong':fmtValue(c.before,null)}`:undefined;
 const show=(c:TCell)=>fmtValue(c.value,c.flag,flagName);
 const download=async()=>{setErr('');try{await downloadApi(`/substations/measurements/${m.id}/xlsx`,
  `pengukuran_${h.substation_code??m.id}_${m.measured_on}_${m.session}.xlsx`)}catch(e){setErr(e instanceof Error?e.message:String(e))}};
 const title=`${h.substation_code??'Gardu'} · ${h.substation_name??''}`;
 const sub=[h.unit_name,`${num(Number(m.snapshot_power_kva),0)} kVA`,`${m.snapshot_line_count} jurusan`,h.feeder_name&&`Penyulang ${h.feeder_name}`].filter(Boolean).join(' · ');
 return <Drawer wide title={title} subtitle={sub} onClose={onClose}
  footer={<>{err&&<span className="vd-err">{err}</span>}<button className="btn secondary" onClick={download}>Unduh Excel</button><button className="btn primary" onClick={onClose}>Tutup</button></>}>
  <div className="vd">
   <dl className="vd-meta">
    <div><dt>Tanggal</dt><dd>{m.measured_on}{m.measured_at?` · ${m.measured_at}`:''}</dd></div>
    <div><dt>Sesi</dt><dd>{h.session_name}</dd></div>
    <div><dt>Status</dt><dd><span className={'vd-state '+m.state}>{stateLabel(m.state)}</span></dd></div>
    <div><dt>Revisi</dt><dd>{m.revision}</dd></div>
    <div><dt>Petugas</dt><dd>{m.technician||'—'}</dd></div>
    <div><dt>Terakhir diubah</dt><dd>{h.updated_by_name??'—'}<small>{whenLabel(m.updated_at)}</small></dd></div>
   </dl>
   <div className="vd-tabs" role="tablist">
    {([['table','Tabel nilai'],['history',`Riwayat (${story.length})`],['raw','Data teknis']] as [Tab,string][]).map(([k,label])=>
     <button key={k} role="tab" aria-selected={tab===k} className={tab===k?'on':''} onClick={()=>setTab(k)}>{label}</button>)}
   </div>
   {tab==='table'&&<div role="tabpanel">
    {t.changedCount>0&&<p className="vd-legend"><i className="vd-swatch"/>{t.changedCount} sel berubah pada revisi terakhir — arahkan kursor ke sel untuk melihat nilai lama.</p>}
    {t.head.length>0&&<div className="vd-scroll"><table className="vd-table">
     <thead><tr><th rowSpan={2} className="vd-rowhead">Jurusan</th>{t.head.map((g,i)=><th key={i} colSpan={g.cols.length} className="vd-grp">{g.title} <span>({g.unit})</span></th>)}</tr>
      <tr>{t.head.flatMap(g=>g.cols.map((c,j)=><th key={c.id} className={j===0?'vd-first':''}>{c.phase&&<i className={'phase-dot phase-'+c.phase} aria-hidden="true"/>}{c.sub||'nilai'}</th>))}</tr></thead>
     <tbody>{t.rows.map(r=><tr key={r.line}><th className="vd-rowhead">{r.label}</th>
      {r.cells.map((c,i)=><td key={c.id} title={tip(c)} className={(c.changed?'vd-changed ':'')+(c.flag?'vd-flag ':'')+(i===0||t.head.some(g=>g.cols[0].id===c.id)?'vd-first':'')}>{show(c)}</td>)}</tr>)}</tbody>
    </table></div>}
    <div className="vd-cards">{t.gardu.map(g=><section key={g.title} className={'vd-card'+(g.tone?' vd-t-'+g.tone:'')}>
     <header>{g.title} <span>({g.unit})</span></header>
     <table><tbody>{g.cells.map(c=><tr key={c.id}><th>{c.phase&&<i className={'phase-dot phase-'+c.phase} aria-hidden="true"/>}{c.sub}</th>
      <td title={tip(c)} className={(c.changed?'vd-changed ':'')+(c.flag?'vd-flag':'')}>{show(c)||<span className="vd-empty">kosong</span>}</td></tr>)}</tbody></table>
    </section>)}</div>
    <ResultPanel data={data.calculated}/>
    {m.note&&<p className="vd-note"><b>Catatan:</b> {m.note}</p>}
   </div>}
   {tab==='history'&&<ol className="vd-story" role="tabpanel">
    {story.map(e=>{const all=open.includes(e.id),lines=all?e.lines:e.lines.slice(0,LIMIT);
     return <li key={e.id} className={'vd-ev vd-'+e.tone}><span className="vd-dot" aria-hidden="true"/>
      <div><p className="vd-sum"><b>{e.summary}</b>{e.revision!=null&&<span className="vd-rev">rev {e.revision}</span>}</p>
       <p className="vd-when">{whenLabel(e.at)}{e.reason&&<> · Alasan: <q>{e.reason}</q></>}</p>
       {lines.length>0&&<ul>{lines.map((l,i)=><li key={i}>{l}</li>)}</ul>}
       {e.lines.length>LIMIT&&<button className="link-btn" onClick={()=>setOpen(all?open.filter(x=>x!==e.id):[...open,e.id])}>{all?'Ringkas':`+${e.lines.length-LIMIT} perubahan lain`}</button>}</div></li>;})}
    {!story.length&&<li className="vd-none">Belum ada riwayat untuk pengukuran ini.</li>}
   </ol>}
   {tab==='raw'&&<div role="tabpanel" className="vd-raw">
    <p>Data mentah untuk pemeriksaan teknis (ID parameter, isi audit apa adanya).</p>
    <button className="btn secondary sm" onClick={()=>setRaw(!raw)}>{raw?'Sembunyikan JSON':'Tampilkan JSON'}</button>
    {raw&&<pre>{JSON.stringify({measurement:m,audit:data.audit},null,2)}</pre>}
   </div>}
  </div>
 </Drawer>;
}
