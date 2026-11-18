import FindingPicker from '../ui/FindingPicker';
import type {AnalysisDefinitions} from '../analysis/types';

type Filter=Record<string,string|string[]>;
type Props={defs:AnalysisDefinitions;filter:Filter;onChange:(next:Filter)=>void;onUseAnalysis:()=>void};
export default function ExportFilter({defs,filter,onChange,onUseAnalysis}:Props){
 const set=(part:Filter)=>onChange({...filter,...part});
 const findings=defs.rules.filter(r=>r.kind==='finding');
 const picked=(filter.findings as string[])??[];
 return <section className="panel export-section"><h3>Sumber dan filter</h3>
  <div className="export-fields">
   <label>Unit<select value={String(filter.unit_id??'')} onChange={e=>set({unit_id:e.target.value})}><option value="">Semua unit yang berhak</option>{defs.units.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select></label>
   <label>Isi baris<select value={String(filter.mode)} onChange={e=>set({mode:e.target.value})}><option value="terakhir">Kondisi terakhir tiap gardu</option><option value="periode">Terbaru dalam periode</option><option value="semua">Semua pengukuran</option></select></label>
   <label>Tanggal mulai<input type="date" value={String(filter.start??'')} onChange={e=>set({start:e.target.value})}/></label>
   <label>Tanggal akhir<input type="date" value={String(filter.end??'')} onChange={e=>set({end:e.target.value})}/></label>
   <label>Sesi<select value={String(filter.session)} onChange={e=>set({session:e.target.value})}><option value="tertinggi">Tertinggi antar sesi</option>{defs.sessions.map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select></label>
   <label>Penyulang<select value={String(filter.feeder_id??'')} onChange={e=>set({feeder_id:e.target.value})}><option value="">Semua penyulang</option>{defs.feeders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
   <label>Kategori<select value={String(filter.category??'')} onChange={e=>set({category:e.target.value})}><option value="">Semua kategori</option>{defs.rules.filter(r=>r.kind==='category').map(r=><option key={r.code} value={r.code}>{r.name}</option>)}</select></label>
   <label>Status ukur<select value={String(filter.status??'')} onChange={e=>set({status:e.target.value})}><option value="">Semua</option><option value="baru">Baru</option><option value="lama">Lama</option><option value="belum">Belum diukur</option></select></label>
   <label>kVA minimum<input inputMode="decimal" value={String(filter.min_kva??'')} onChange={e=>set({min_kva:e.target.value})}/></label>
   <label>kVA maksimum<input inputMode="decimal" value={String(filter.max_kva??'')} onChange={e=>set({max_kva:e.target.value})}/></label>
   <label>Cari gardu<input value={String(filter.text??'')} maxLength={180} onChange={e=>set({text:e.target.value})} placeholder="Kode, nama, alamat, merk"/></label>
  </div>
  <FindingPicker findings={findings} picked={picked} mode={String(filter.finding_mode||'any')} onChange={(next,finding_mode)=>set({findings:next,finding_mode})}/>
  <div className="export-actions"><button className="btn secondary" onClick={onUseAnalysis}>Pakai filter dari Analisa</button></div>
 </section>;
}
