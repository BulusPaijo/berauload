import UnitMetricOptions from '../unit-references/UnitMetricOptions';
import { useEffect, useState, type FormEvent } from 'react';
import { Calculator, ChevronRight, Plus, Save, X } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, isoWita, num, qs, type Catalog, type User } from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import {SourceStatusSummary,type Status} from '../unit-references/SourceStatus';
import '../parameters/parameters.css';
import './historical.css';
import ListControls,{PAGE_SIZE} from '../../shared/ListControls';
import type {UnitItem} from '../units/UnitManager';

type Mode = 'period' | 'moving_avg' | 'yoy';
type Resolution = 'day' | 'month' | 'year';
type Aggregation = 'AVG' | 'MAX' | 'MIN' | 'SUM';
type Definition = {
  id?: number; code: string; name: string; expression: string; unit: string;
  mode: Mode; aggregation: Aggregation; resolution: Resolution;
  moving_days: number; hour_start: number; hour_end: number; version?: number; archived?: boolean;
};
type ResultRow = {
  period: string; value: number | null; count: number; expected: number;
  coverage_pct: number; complete: boolean; comparable?: boolean;
  previous_value?: number | null; current_value?: number | null;
};
type CalcResult = { source_status?:Status; data: ResultRow[]; result_unit: string; skipped_incomplete_hours: number; note: string };
// Role-resolved presets are created in the component, not persisted defaults.
const today = isoWita();
const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error);
const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
const createTemplate=(CAP:string,LOAD:string): Definition => ({
  code: 'rata_cadangan_bulanan', name: 'Rata-rata Cadangan Daya Bulanan',
  expression: `${CAP} - ${LOAD}`, unit: 'kW', mode: 'period', aggregation: 'AVG',
  resolution: 'month', moving_days: 7, hour_start: 0, hour_end: 23,
});
const createPresets=(CAP:string,LOAD:string,TEMPLATE:Definition) => [
  { label: 'Rata-rata cadangan daya', patch: TEMPLATE },
  { label: 'Puncak beban malam', patch: { ...TEMPLATE, code: 'puncak_beban_malam', name: 'Puncak Beban Malam', expression: LOAD, aggregation: 'MAX' as Aggregation, resolution: 'day' as Resolution, hour_start: 18, hour_end: 22 } },
  { label: 'Jam beban melebihi daya mampu', patch: { ...TEMPLATE, code: 'jam_cadangan_negatif', name: 'Jam Beban > Daya Mampu', expression: `IF(${LOAD} > ${CAP}, 1, 0)`, unit: '1', aggregation: 'SUM' as Aggregation } },
  { label: 'Pertumbuhan puncak YoY', patch: { ...TEMPLATE, code: 'growth_puncak_yoy', name: 'Pertumbuhan Puncak Beban YoY', expression: LOAD, mode: 'yoy' as Mode, aggregation: 'MAX' as Aggregation } },
  { label: 'Moving average 7 hari', patch: { ...TEMPLATE, code: 'ma7_beban', name: 'Rata-rata Bergerak Beban 7 Hari', expression: LOAD, mode: 'moving_avg' as Mode, aggregation: 'AVG' as Aggregation, resolution: 'day' as Resolution } },
];
const defaultStart = `${today.slice(0, 4)}-01-01`;

export default function HistoricalCalculations({ catalog, user }: { catalog: Catalog; user: User }) {
  const referenceMetrics=useUnitMetricReferences();
  const metricOptions=metricsForSelection(referenceMetrics,catalog.metrics);
  const CAP=catalog.roles?.['system.capacity']||'';
  const LOAD=catalog.roles?.['system.load']||'';
  const TEMPLATE=createTemplate(CAP,LOAD);
  const PRESETS=CAP&&LOAD?createPresets(CAP,LOAD,TEMPLATE):[];
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [unitOptions,setUnitOptions]=useState<UnitItem[]>([]);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnitOptions).catch(()=>{});},[]);
  const [status,setStatus]=useState('active');
  const [search,setSearch]=useState('');
  const [page,setPage]=useState(1);
  const [selected, setSelected] = useState<Definition | null>(null);
  const [form, setForm] = useState<Definition>(TEMPLATE);
  const [drawer, setDrawer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(today);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [metricInsert, setMetricInsert] = useState(LOAD);
  const [preset, setPreset] = useState('0');
  const [editId, setEditId] = useState<number | null>(null);
  const [changeReason, setChangeReason] = useState('');
  const [history, setHistory] = useState<{ version: number; reason: string }[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

  async function refresh() {
    const rows = await api<Definition[]>('/historical-calculations' + (user.role === 'admin' ? '?include_archived=true' : ''));
    setDefinitions(rows);
  }
  useEffect(() => { refresh().catch(e => setError(messageOf(e))); }, []);
  useEffect(() => {
    if (!drawer) return;
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) setDrawer(false); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [drawer, busy]);

  function openNew() {
    setForm({ ...TEMPLATE }); setPreset('0'); setSelected(null); setEditId(null); setChangeReason('');
    setResult(null); setError(''); setNotice(''); setDrawer(true);
  }
  function openEdit(definition: Definition) {
    setForm({ ...definition }); setEditId(definition.id ?? null); setChangeReason(''); setSelected(null);
    setResult(null); setError(''); setDrawer(true);
  }
  function duplicate(definition: Definition) {
    setForm({ ...definition, id: undefined, version: undefined, archived: false,
      code: `${definition.code}_salinan`, name: `${definition.name} (Salinan)` });
    setEditId(null); setSelected(null); setResult(null); setChangeReason(''); setError(''); setDrawer(true);
  }
  function patchForm(patch: Partial<Definition>) {
    setForm(current => ({ ...current, ...patch }));
    setResult(null); setError('');
  }
  function usePreset(index: string) {
    if(!PRESETS[Number(index)])return;
    setPreset(index); patchForm({ ...PRESETS[Number(index)].patch });
  }
  async function preview(event?: FormEvent) {
    event?.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const data = await api<CalcResult>('/historical-calculations/preview', {
        method: 'POST', body: JSON.stringify({ ...form, start, end }),
      });
      setResult(data); setNotice('Simulasi berhasil. Tidak ada data historis yang diubah.');
    } catch (e) { setError(messageOf(e)); setResult(null); }
    finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setError('');
    try {
      if (editId && changeReason.trim().length < 5) throw new Error('Alasan revisi minimal 5 karakter');
      const saved = await api<Definition>(editId ? `/historical-calculations/${editId}/revisions` : '/historical-calculations', {
        method: 'POST', body: JSON.stringify(editId ? { ...form, expected_version: form.version, reason: changeReason } : form),
      });
      setDrawer(false); setEditId(null); setSelected(saved); setSelectedVersion(null);
      setNotice(`Formula berhasil disimpan pada versi ${saved.version}.`);
      await refresh(); await runSaved(saved);
    } catch (e) { setError(messageOf(e)); }
    finally { setBusy(false); }
  }
  async function runSaved(definition: Definition, version?: number | null) {
    setSelected(definition); setSelectedVersion(version ?? null); setLoading(true); setError('');
    try {
      const search = qs({ start, end, ...(version ? { version } : {}) });
      const data = await api<CalcResult>(`/historical-calculations/${definition.id}/run?${search}`);
      setResult(data);
    } catch (e) { setError(messageOf(e)); setResult(null); }
    finally { setLoading(false); }
  }
  async function manageArchive(definition: Definition) {
    if (changeReason.trim().length < 5) { setError('Isi alasan arsip/pemulihan (minimal 5 karakter).'); return; }
    setBusy(true); setError('');
    try {
      const updated = await api<Definition>(`/historical-calculations/${definition.id}/archive`, { method: 'PATCH',
        body: JSON.stringify({ archived: !definition.archived, reason: changeReason }) });
      setStatus(updated.archived?'archived':'active'); setPage(1); setSelected(updated); setResult(null); setChangeReason('');
      setNotice(updated.archived ? 'Formula diarsipkan, versi lamanya tetap dapat diperiksa.' : 'Formula dipulihkan.');
      await refresh();
    } catch (e) { setError(messageOf(e)); } finally { setBusy(false); }
  }
  async function loadHistory(definition: Definition) {
    try {
      const items = await api<{ version: number; reason: string }[]>(`/historical-calculations/${definition.id}/revisions`);
      setHistory(items); setSelected(definition); setSelectedVersion(null);
    } catch (e) { setError(messageOf(e)); }
  }
  const filtered=definitions.filter(d=>(status==='all'||Boolean(d.archived)===(status==='archived')) &&
    `${d.name} ${d.code}`.toLowerCase().includes(search.toLowerCase()));
  const paged=filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  const active = selected || form;
  const unit = result?.result_unit || (active.mode === 'yoy' ? '%' : active.unit);
  const values = result?.data.filter(r => r.value !== null) || [];
  const incomplete = result?.data.filter(r => !r.complete).length || 0;
  const unitLabel = unit === 'jam' ? 'interval jam tercatat' : unit;

  return <div className="historical-feature">
    <div className="panel">
      <div className="panel-head parameter-toolbar">
        <div><h3>Formula Historis</h3><p>Rumus Excel-like V1.1, dihitung lintas waktu tanpa mengubah pembacaan lama.</p></div>
        {user.role === 'admin' && <button type="button" className="btn primary sm" onClick={openNew}><Plus size={16}/> Tambah Perhitungan</button>}
      </div>
      <ListControls search={search} onSearch={setSearch} status={status} onStatus={setStatus}
        options={[{value:'active',label:'Aktif'},{value:'archived',label:'Arsip'},{value:'all',label:'Semua'}]}
        page={page} onPage={setPage} count={filtered.length}/>
      <div className="historical-definition-list">
        {paged.map(d => <button key={d.id} type="button" className={selected?.id === d.id ? 'historical-definition selected' : 'historical-definition'} onClick={() => { setHistory([]); if (d.archived) { setSelected(d); setResult(null); setError(''); } else { runSaved(d).catch(e => setError(messageOf(e))); } }}>
          <span><b>{d.name}</b><small>{d.code} · v{d.version} · {d.mode} · {d.aggregation} / {d.resolution}{d.archived ? ' · DIARSIPKAN' : ''}</small></span><ChevronRight size={17}/>
        </button>)}
        {!filtered.length && <div className="empty">Belum ada formula historis. Admin dapat membuat dari contoh siap pakai.</div>}
      </div>
    </div>
    <section className="panel historical-output">
      <div className="panel-head"><h3>Hasil Kalkulasi {selected ? `— ${selected.name}` : '(Pratinjau)'}</h3></div>
      <div className="historical-period">
        <label>Mulai<input type="date" value={start} onChange={e => setStart(e.target.value)}/></label>
        <label>Sampai<input type="date" value={end} onChange={e => setEnd(e.target.value)}/></label>
        {selected && !selected.archived && <button type="button" className="btn secondary sm" disabled={loading} onClick={() => runSaved(selected, selectedVersion)}>Hitung ulang</button>}
      </div>
      {selected && <div className="historical-management">
        <strong>Kelola formula · versi aktif {selected.version} {selected.archived ? '(arsip)' : ''}</strong>
        <div className="historical-actions">
          <button type="button" className="btn secondary sm" onClick={() => loadHistory(selected)}>Riwayat versi</button>
          {user.role === 'admin' && !selected.archived && <button type="button" className="btn secondary sm" onClick={() => openEdit(selected)}>Edit / Revisi</button>}
          {user.role === 'admin' && <button type="button" className="btn secondary sm" onClick={() => duplicate(selected)}>Duplikasi</button>}
        </div>
        {history.length > 0 && <label>Jalankan versi terdahulu
          <select value={selectedVersion ?? ''} onChange={e => runSaved(selected, e.target.value ? Number(e.target.value) : null)}>
            <option value="">Versi terkini</option>{history.map(r => <option key={r.version} value={r.version}>Versi {r.version} — {r.reason}</option>)}
          </select></label>}
        {user.role === 'admin' && <div className="historical-actions">
          <input aria-label="Alasan arsip atau pemulihan" placeholder="Alasan arsip/pemulihan (min. 5 karakter)" value={changeReason} onChange={e => setChangeReason(e.target.value)}/>
          <button type="button" className="btn secondary sm" disabled={busy} onClick={() => manageArchive(selected)}>{selected.archived ? 'Pulihkan' : 'Arsipkan'}</button>
        </div>}
      </div>}
      {error && <div className="notice error" role="alert">{error}</div>}

      {notice && <div className="notice success" role="status">{notice}</div>}
      {loading && <div className="loading">Menghitung histori...</div>}
      {result && <>
        <div className="historical-summary">
          <span><b>{values.length}</b><small>Periode bernilai</small></span>
          <span><b>{incomplete}</b><small>Periode belum lengkap</small></span>
          <span><b>{unitLabel}</b><small>Satuan hasil</small></span>
        </div>
        <div className="historical-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.data} margin={{ top: 14, right: 24, bottom: 16, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="period" minTickGap={24}/><YAxis width={65}/>
          <Tooltip formatter={value => `${num(Number(value), 3)} ${unitLabel}`}/>
          <Line type="monotone" dataKey="value" name={active.name} stroke="#087f8c" strokeWidth={2.5} dot={false} connectNulls={false}/>
        </LineChart></ResponsiveContainer></div>
        <p className="parameter-hint">{result.note} YoY parsial bukan pertumbuhan resmi. SUM indikator 0/1 menghitung jumlah interval tercatat, bukan energi MWh.</p>
        <div className="scroll-table"><table><thead><tr><th>Periode</th><th>Hasil</th><th>Jam Valid</th><th>Kelengkapan</th><th>Status</th></tr></thead><tbody>
          {result.data.map(row => <tr key={row.period}><td>{row.period}</td><td className="mono">{num(row.value, 3)} {row.value === null ? '' : unitLabel}</td><td>{row.count}/{row.expected}</td>
            <td>{num(row.coverage_pct, 1)}%</td><td><span className={'tag ' + (row.complete ? 'success' : 'warning')}>{row.complete ? 'Lengkap' : 'Parsial'}</span></td></tr>)}
        </tbody></table></div>
      </>}
      <SourceStatusSummary status={result?.source_status}/>
      {!result && !loading && <p className="empty">Pilih formula tersimpan atau buat perhitungan baru untuk melihat hasilnya.</p>}
    </section>

    {drawer && <div className="drawer-overlay" onMouseDown={e => { if (e.target === e.currentTarget && !busy) setDrawer(false); }}>
      <aside className="parameter-drawer historical-drawer" role="dialog" aria-modal="true" aria-label="Tambah atau Revisi Formula Historis">
        <div className="drawer-heading"><div><span className="eyebrow">V1.2 · HISTORICAL CALCULATION</span><h3>{editId ? `Revisi Formula V${form.version}` : "Buat Formula Historis"}</h3></div>
          <button className="drawer-close" type="button" aria-label="Tutup panel" disabled={busy} onClick={() => setDrawer(false)}><X size={22}/></button></div>
        <div className="drawer-body"><form className="parameter-form" onSubmit={preview}>
          {!editId && <label>Contoh siap pakai<select value={preset} onChange={e => usePreset(e.target.value)}>{PRESETS.map((p, i) => <option key={i} value={String(i)}>{p.label}</option>)}</select></label>}
          <label>Nama perhitungan<input value={form.name} required minLength={2} maxLength={180} onChange={e => patchForm({ name: e.target.value, ...(editId ? {} : { code: slug(e.target.value) }) })}/></label>
          <label>Kode unik<input value={form.code} disabled={!!editId} required minLength={2} maxLength={90} pattern="[a-z][a-z0-9_]*" onChange={e => patchForm({ code: e.target.value.toLowerCase() })}/></label>
          <div className="parameter-form-grid">
            <label>Jenis<select value={form.mode} onChange={e => patchForm({ mode: e.target.value as Mode, resolution: e.target.value === 'yoy' ? 'month' : e.target.value === 'moving_avg' ? 'day' : form.resolution, aggregation: e.target.value === 'moving_avg' ? 'AVG' : form.aggregation })}>
              <option value="period">Periode biasa</option><option value="moving_avg">Moving Average</option><option value="yoy">Pertumbuhan YoY</option></select></label>
            <label>Agregasi<select disabled={form.mode === 'moving_avg'} value={form.aggregation} onChange={e => patchForm({ aggregation: e.target.value as Aggregation })}>
              <option value="AVG">Rata-rata</option><option value="MAX">Puncak (MAX)</option><option value="MIN">Minimum</option><option value="SUM">Jumlah interval (SUM)</option></select></label>
          </div>
          <div className="parameter-form-grid">
            <label>Resolusi<select disabled={form.mode !== 'period'} value={form.resolution} onChange={e => patchForm({ resolution: e.target.value as Resolution })}><option value="day">Harian</option><option value="month">Bulanan</option><option value="year">Tahunan</option></select></label>
            <label>Satuan ekspresi<select value={form.unit} onChange={e => patchForm({ unit: e.target.value })}>{unitOptions.filter(u=>u.active||u.code===form.unit).map(u => <option key={u.code} value={u.code}>{u.code} — {u.name}</option>)}</select></label>
          </div>
          {form.mode === 'moving_avg' && <label>Jendela hari (2–30)<input type="number" min={2} max={30} value={form.moving_days} onChange={e => patchForm({ moving_days: Number(e.target.value) })}/></label>}
          <div className="parameter-form-grid">
            <label>Jam mulai (WITA)<input type="number" min={0} max={23} value={form.hour_start} onChange={e => patchForm({ hour_start: Number(e.target.value) })}/></label>
            <label>Jam akhir (WITA)<input type="number" min={0} max={23} value={form.hour_end} onChange={e => patchForm({ hour_end: Number(e.target.value) })}/></label>
          </div>
          <label>Formula Excel-like (tanpa Python)<textarea rows={3} value={form.expression} onChange={e => patchForm({ expression: e.target.value })} required maxLength={500}/></label>
          <div className="historical-insert"><select aria-label="Pilih parameter untuk rumus" value={metricInsert} onChange={e => setMetricInsert(e.target.value)}>
            <UnitMetricOptions metrics={metricOptions.filter(m => m.active)}/>
          </select><button type="button" className="btn secondary sm" onClick={() => patchForm({ expression: `${form.expression} ${metricInsert}`.trim() })}><Plus size={14}/> Sisipkan</button></div>
          <p className="parameter-hint">Operasi V1.1 tetap dipakai: +, −, *, /, SUM, AVG, MIN, MAX, IF. Agregasi di atas diterapkan terhadap hasil tiap jam. Data kosong tidak dianggap nol.</p>
          {error && <div className="notice error" role="alert">{error}</div>}
          {result && !selected && <div className="historical-preview" role="status">
            <b>Pratinjau: {result.data.length} periode</b>
            <small>Hasil dihitung tanpa menyimpan atau mengubah data jam.</small>
            {result.data.slice(0, 4).map(row => <div key={row.period}><span>{row.period}</span>
              <strong>{num(row.value, 3)} {row.value === null ? '' : result.result_unit}</strong></div>)}
            {result.data.length > 4 && <small>Hasil lengkap tersedia di panel analisis.</small>}
          </div>}
          {editId && <label>Alasan revisi (wajib)<textarea rows={2} value={changeReason} maxLength={500} onChange={e => setChangeReason(e.target.value)} placeholder="Jelaskan perubahan rumus dan alasan teknisnya"/></label>}
          <div className="historical-actions"><button type="submit" className="btn secondary" disabled={busy}><Calculator size={16}/> {busy ? 'Memeriksa...' : 'Uji dengan histori'}</button>
          <button type="button" className="btn primary" disabled={busy} onClick={save}><Save size={16}/> {editId ? "Simpan Versi Baru" : "Simpan Formula"}</button></div>
        </form></div>
      </aside>
    </div>}
  </div>;
}
