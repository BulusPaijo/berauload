import { useEffect, useState } from 'react';
import { Calculator, Plus, Save, X } from 'lucide-react';
import { api, isoWita, num, qs, type Catalog, type User } from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import {SourceStatusSummary,type Status as SourceStatusType} from '../unit-references/SourceStatus';
import '../parameters/parameters.css';
import '../historical/historical.css';
import './engineering.css';
import ListControls,{PAGE_SIZE} from '../../shared/ListControls';
import type {UnitItem} from '../units/UnitManager';

type Direction = 'below' | 'above';
type Status = 'draft' | 'active' | 'archived';
type Rule = {
  id?: number; code: string; name: string; expression: string; unit: string;
  direction: Direction; warning_threshold: number; critical_threshold: number;
  effective_from: string; reference_note: string; version?: number; status?: Status;
};
type Preview = { result: { value: number | null; status: string; missing?: string[]; reason?: string } };
type History = {
  source_status?:SourceStatusType; evaluated_version: number; evaluated_unit: string;
  expected_hours: number; valid_hours: number; coverage_pct: number;
  missing_or_invalid_hours: number; events_capped: boolean;
  status_counts: Record<string, number>;
  events: { day: string; hour: number; value: number; status: string }[];
};
// The role sources come from the catalog for the current unit.
const emptyRule = (cap:string,load:string): Rule => ({ code: '', name: '', expression: `${cap} - ${load}`, unit: 'kW',
  direction: 'below', warning_threshold: NaN, critical_threshold: NaN,
  effective_from: isoWita(), reference_note: '' });
const message = (e: unknown) => e instanceof Error ? e.message : String(e);
const codeFor = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
const statusName: Record<string, string> = { normal: 'Normal', warning: 'Waspada', critical: 'Kritis',
  no_data: 'Data belum lengkap', invalid: 'Tidak valid' };

export default function EngineeringRules({ catalog, user }: { catalog: Catalog; user: User }) {
  const cap=catalog.roles?.['system.capacity']||'';
  const load=catalog.roles?.['system.load']||'';
  const [rules, setRules] = useState<Rule[]>([]);
  const [unitOptions,setUnitOptions]=useState<UnitItem[]>([]);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnitOptions).catch(()=>{});},[]);
  const [status,setStatus]=useState('active');
  const [search,setSearch]=useState('');
  const [page,setPage]=useState(1);
  const [selected, setSelected] = useState<Rule | null>(null);
  const [form, setForm] = useState<Rule>(()=>emptyRule(cap,load));
  const [editId, setEditId] = useState<number | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [sample, setSample] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<Preview | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [revisions, setRevisions] = useState<{ version: number; reason: string }[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [start, setStart] = useState(`${isoWita().slice(0, 7)}-01`);
  const [end, setEnd] = useState(isoWita());
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const referenceMetrics=useUnitMetricReferences();
  const metricOptions=metricsForSelection(referenceMetrics,catalog.metrics);
  const samplesUsed = metricOptions.filter(m => form.expression.split(/[^a-zA-Z0-9_]+/).includes(m.code));

  async function refresh() { setRules(await api<Rule[]>('/engineering-rules')); }
  useEffect(() => { refresh().catch(e => setError(message(e))); }, []);
  const setField = (partial: Partial<Rule>) => { setForm(v => ({ ...v, ...partial })); setPreview(null); };
  const openNew = () => { setEditId(null); setForm(emptyRule(cap,load)); setSample({}); setPreview(null); setReason(''); setError(''); setDrawer(true); };
  const openEdit = (rule: Rule) => { setEditId(rule.id || null); setForm(rule); setPreview(null); setReason(''); setError(''); setDrawer(true); };
  const payload = () => {
    if (!Number.isFinite(form.warning_threshold) || !Number.isFinite(form.critical_threshold)) {
      throw new Error('Isi kedua ambang batas teknis sesuai ketentuan yang disetujui.');
    }
    return form;
  };
  async function runPreview() {
    setBusy(true); setError('');
    try {
      const data = await api<Preview>('/engineering-rules/preview', { method: 'POST',
        body: JSON.stringify({ ...payload(), samples: Object.fromEntries(
          Object.entries(sample).filter(([, v]) => v.trim() !== '').map(([k, v]) => [k, Number(v)]) ) }) });
      setPreview(data);
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setError('');
    try {
      if (editId && reason.trim().length < 5) throw new Error('Isi alasan revisi minimal 5 karakter');
      const body = editId ? { ...payload(), expected_version: form.version, reason } : payload();
      const path = editId ? `/engineering-rules/${editId}/revisions` : '/engineering-rules';
      const rule = await api<Rule>(path, { method: 'POST', body: JSON.stringify(body) });
      setStatus('draft'); setPage(1); setSelected(rule); setDrawer(false); setHistory(null); setRevisions([]); setSelectedVersion(null);
      setNotice(`Aturan versi ${rule.version} tersimpan sebagai DRAFT. Aktifkan setelah diverifikasi.`);
      await refresh();
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function action(actionName: 'activate' | 'archive') {
    if (!selected) return;
    if (reason.trim().length < 5) { setError('Isi alasan keputusan minimal 5 karakter.'); return; }
    setBusy(true); setError('');
    try {
      const updated = await api<Rule>(`/engineering-rules/${selected.id}/${actionName}`, {
        method: 'POST', body: JSON.stringify({ reason }) });
      setStatus(actionName==='activate'?'active':'archived'); setPage(1); setSelected(updated); setReason(''); setHistory(null); setRevisions([]); setSelectedVersion(null); setNotice(
        actionName === 'activate' ? 'Aturan aktif untuk analisis advisory.' : 'Aturan diarsipkan.');
      await refresh();
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function loadRevisions() {
    if (!selected) return;
    try { setRevisions(await api<{version:number;reason:string}[]>(`/engineering-rules/${selected.id}/revisions`)); }
    catch (e) { setError(message(e)); }
  }
  async function runHistory() {
    if (!selected) return;
    setBusy(true); setError('');
    try { setHistory(await api<History>(`/engineering-rules/${selected.id}/history?${qs({ start, end, ...(selectedVersion ? { version: selectedVersion } : {}) })}`)); }
    catch (e) { setError(message(e)); setHistory(null); } finally { setBusy(false); }
  }

  const filtered=rules.filter(r=>(status==='all'||r.status===status) &&
    `${r.name} ${r.code}`.toLowerCase().includes(search.toLowerCase()));
  const paged=filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  return <div className="historical-feature engineering-feature">
    <div className="panel">
      <div className="panel-head parameter-toolbar"><div><h3>Aturan Teknis</h3><p>Evaluasi status berdasarkan batas yang ditetapkan admin, bukan batas bawaan aplikasi.</p></div>
        {user.role === 'admin' && <button className="btn primary sm" onClick={openNew}><Plus size={15}/> Tambah Rule</button>}</div>
      <ListControls search={search} onSearch={setSearch} status={status} onStatus={setStatus}
        options={[{value:'active',label:'Aktif'},{value:'draft',label:'Draft'},{value:'archived',label:'Arsip'},{value:'all',label:'Semua'}]}
        page={page} onPage={setPage} count={filtered.length}/>
      <div className="historical-definition-list">{paged.map(r => <button key={r.id} type="button"
        className={'historical-definition ' + (selected?.id === r.id ? 'selected' : '')}
        onClick={() => { setSelected(r); setHistory(null); setError(''); setRevisions([]); setSelectedVersion(null); }}>
        <span><b>{r.name}</b><small>{r.code} · v{r.version} · {r.unit} · {r.status === 'active' ? 'AKTIF' : r.status === 'draft' ? 'DRAFT' : 'ARSIP'}</small></span>
        <span className={'rule-status ' + (r.status || 'draft')}>{r.status}</span></button>)}
        {!filtered.length && <div className="empty">Belum ada aturan. Tidak ada ambang batas yang disetel otomatis.</div>}</div>
    </div>
    <section className="panel rule-workspace">
      <div className="panel-head"><h3>{selected ? selected.name : 'Evaluasi Engineering Rules'}</h3></div>
      {!selected && <p className="empty">Pilih aturan untuk melihat ketentuan, status aktivasi, dan hasil evaluasi historis.</p>}
      {selected && <div className="rule-detail">
        <div className="rule-facts"><span><small>Formula</small><code>{selected.expression}</code></span>
          <span><small>Batas waspada</small><strong>{num(selected.warning_threshold, 4)} {selected.unit}</strong></span>
          <span><small>Batas kritis</small><strong>{num(selected.critical_threshold, 4)} {selected.unit}</strong></span></div>
        <p className="muted small">Arah: {selected.direction === 'below' ? 'Nilai semakin rendah semakin perlu perhatian' : 'Nilai semakin tinggi semakin perlu perhatian'}.
          Mulai berlaku: {selected.effective_from}. Sumber ketentuan: {selected.reference_note}</p>
        {user.role === 'admin' && selected.status !== 'archived' && <div className="rule-approval">
          <input aria-label="Alasan aktivasi atau arsip" placeholder="Alasan keputusan (min. 5 karakter)" value={reason} onChange={e => setReason(e.target.value)}/>
          <div className="historical-actions">
            <button className="btn secondary sm" onClick={() => openEdit(selected)}>Edit / Revisi</button>
            {selected.status === 'draft' && <button className="btn primary sm" disabled={busy} onClick={() => action('activate')}>Aktifkan</button>}
            <button className="btn secondary sm" disabled={busy} onClick={() => action('archive')}>Arsipkan</button>
          </div></div>}
        <div className="historical-actions"><button type="button" className="btn secondary sm" onClick={loadRevisions}>Lihat Riwayat Versi</button></div>
        {revisions.length > 0 && <label>Jalankan versi aturan tertentu
          <select value={selectedVersion ?? ''} onChange={e => { setSelectedVersion(e.target.value ? Number(e.target.value) : null); setHistory(null); }}>
            <option value="">Versi aktif</option>{revisions.map(r => <option key={r.version} value={r.version}>V{r.version} — {r.reason}</option>)}
          </select></label>}
        <div className="historical-period"><label>Dari<input type="date" value={start} onChange={e => setStart(e.target.value)}/></label>
          <label>Sampai<input type="date" value={end} onChange={e => setEnd(e.target.value)}/></label>
          <button type="button" className="btn secondary sm" onClick={runHistory} disabled={busy || (selected.status !== 'active' && !selectedVersion)}>Evaluasi Histori</button></div>
        {selected.status !== 'active' && !selectedVersion && <p className="parameter-hint">Draft/arsip tidak dievaluasi sebagai aturan aktif. Admin dapat simulasi dari editor.</p>}
      </div>}
      {error && <div className="notice error" role="alert">{error}</div>}
      {notice && <div className="notice success" role="status">{notice}</div>}
      {history && <div className="rule-history"><p className="muted small">Evaluasi versi {history.evaluated_version}</p>
        <div className="historical-summary"><span><b>{history.valid_hours}/{history.expected_hours}</b><small>Jam Valid</small></span>
          <span><b>{num(history.coverage_pct, 2)}%</b><small>Kelengkapan</small></span>
          <span><b>{history.missing_or_invalid_hours}</b><small>Belum lengkap/invalid</small></span></div>
        <div className="rule-counts">{(['normal', 'warning', 'critical'] as const).map(s =>
          <span key={s} className={'rule-status ' + s}>{statusName[s]}: {history.status_counts[s] ?? 0} jam</span>)}</div><SourceStatusSummary status={history.source_status}/>
        <div className="scroll-table"><table><thead><tr><th>Tanggal (WITA)</th><th>Jam</th><th>Nilai</th><th>Status</th></tr></thead><tbody>
          {history.events.map((e, index) => <tr key={`${e.day}-${e.hour}-${index}`}><td>{e.day}</td><td>{String(e.hour).padStart(2, '0')}:00</td>
            <td>{num(e.value, 3)} {history.evaluated_unit}</td><td>{statusName[e.status]}</td></tr>)}
        </tbody></table>{!history.events.length && <p className="empty">Tidak ditemukan kejadian waspada/kritis pada jam dengan data valid.</p>}</div>
        <p className="parameter-hint">Evaluasi historis hanya bersifat advisory, bukan alarm real-time atau kendali pembangkit.
          {history.events_capped ? ' Daftar dibatasi 500 kejadian, jumlah total tetap dihitung.' : ''}</p>
      </div>}
    </section>
    {drawer && <div className="drawer-overlay" onMouseDown={e => { if (e.target === e.currentTarget && !busy) setDrawer(false); }}>
      <aside className="parameter-drawer historical-drawer" role="dialog" aria-modal="true" aria-label="Atur Engineering Rule">
        <div className="drawer-heading"><div><span className="eyebrow">V1.3 · ENGINEERING RULES</span><h3>{editId ? 'Revisi Aturan' : 'Tambah Aturan'}</h3></div>
          <button type="button" className="drawer-close" aria-label="Tutup" onClick={() => setDrawer(false)}><X size={21}/></button></div>
        <div className="drawer-body parameter-form">
          <label>Nama aturan<input required value={form.name} onChange={e => setField({ name: e.target.value,
            ...(editId ? {} : { code: codeFor(e.target.value) }) })}/></label>
          <label>Kode unik<input disabled={!!editId} required value={form.code} onChange={e => setField({ code: e.target.value })}/></label>
          <label>Ekspresi Formula V1.1<textarea rows={3} value={form.expression} onChange={e => setField({ expression: e.target.value })}/></label>
          <p className="parameter-hint">Sumber contoh: parameter system.capacity − system.load. Data input harus tersedia pada jam yang dievaluasi.</p>
          <div className="parameter-form-grid"><label>Satuan<select value={form.unit} onChange={e => setField({ unit: e.target.value })}>
            {unitOptions.filter(u=>u.active||u.code===form.unit).map(u => <option key={u.code} value={u.code}>{u.code} — {u.name}</option>)}</select></label>
            <label>Arah kondisi<select value={form.direction} onChange={e => setField({ direction: e.target.value as Direction })}>
              <option value="below">Di bawah batas</option><option value="above">Di atas batas</option></select></label></div>
          <div className="parameter-form-grid"><label>Batas WASPADA<input type="number" step="any" value={Number.isFinite(form.warning_threshold) ? form.warning_threshold : ''}
            onChange={e => setField({ warning_threshold: e.target.value === '' ? NaN : Number(e.target.value) })}/></label>
            <label>Batas KRITIS<input type="number" step="any" value={Number.isFinite(form.critical_threshold) ? form.critical_threshold : ''}
            onChange={e => setField({ critical_threshold: e.target.value === '' ? NaN : Number(e.target.value) })}/></label></div>
          <label>Mulai berlaku<input type="date" value={form.effective_from} onChange={e => setField({ effective_from: e.target.value })}/></label>
          <label>Dasar/sumber ketentuan teknis<textarea rows={2} maxLength={500} value={form.reference_note}
            onChange={e => setField({ reference_note: e.target.value })} placeholder="Dokumen keputusan atau persetujuan batas operasi"/></label>
          <h4>Uji dengan angka contoh</h4>
          {samplesUsed.map(m => <label key={m.code}>{m.name} ({m.unit})<input type="number" step="any"
            value={sample[m.code] || ''} onChange={e => setSample(old => ({ ...old, [m.code]: e.target.value }))}/></label>)}
          <button type="button" className="btn secondary" disabled={busy} onClick={runPreview}><Calculator size={15}/> Uji Formula & Batas</button>
          {preview && <div className="historical-preview"><strong>{statusName[preview.result.status] || preview.result.status}</strong>
            <span>{preview.result.value == null ? 'Data belum lengkap' : `${num(preview.result.value, 3)} ${form.unit}`}</span>
            {!!preview.result.missing?.length && <small>Kurang: {preview.result.missing.join(', ')}</small>}</div>}
          {editId && <label>Alasan revisi<input value={reason} onChange={e => setReason(e.target.value)} placeholder="Wajib minimal 5 karakter"/></label>}
          {error && <div className="notice error" role="alert">{error}</div>}
          <button type="button" className="btn primary" disabled={busy} onClick={save}><Save size={15}/> {editId ? 'Simpan Versi Baru sebagai Draft' : 'Simpan sebagai Draft'}</button>
        </div></aside></div>}
  </div>;
}
