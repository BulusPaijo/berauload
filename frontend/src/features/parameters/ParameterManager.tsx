import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Calculator, Pencil, Plus, SlidersHorizontal, X } from 'lucide-react';
import { api, type Catalog, type Metric } from '../../api';
import FormulaBuilder from '../formulas/FormulaBuilder';
import './parameters.css';
import ListControls,{PAGE_SIZE} from '../../shared/ListControls';
import type {InputFormConfig} from '../input-form/types';
import type {UnitItem} from '../units/UnitManager';

const GROUPS = ['PEMBANGKIT', 'KUALITAS', 'FEEDER', 'REKAP', 'REKAP_LAIN'];

type Mode = 'input' | 'computed';
type ExistingFormula = { code: string; expression: string; version: number };
type EditState = { metric: Metric; name: string; active: boolean; role_key: string };
const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error);

export default function ParameterManager({ catalog, refreshCatalog }: {
  catalog: Catalog;
  refreshCatalog: () => void;
}) {
  const [kind, setKind] = useState<Mode | null>(null);
  const [editing, setEditing] = useState<EditState | null>(null);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [status,setStatus]=useState('active');
  const [page,setPage]=useState(1);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [unit, setUnit] = useState('kW');
  const [group, setGroup] = useState('PEMBANGKIT');
  const [assetId, setAssetId] = useState('');
  const [inputTab,setInputTab]=useState('PEMBANGKIT');
  const [units,setUnits]=useState<UnitItem[]>([]);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnits).catch(()=>{});},[]);
  const [formTabs,setFormTabs]=useState<{code:string;name:string}[]>([]);
  useEffect(()=>{api<InputFormConfig>('/input-form/config').then(c=>setFormTabs(c.tabs.filter(t=>t.active))).catch(()=>{});},[]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [formulas, setFormulas] = useState<ExistingFormula[]>([]);
  const open = kind !== null || editing !== null;

  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') close(); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [open]);

  function close() { setKind(null); setEditing(null); setError(''); }
  function startCreate(mode: Mode) {
    setEditing(null); setKind(mode); setError(''); setNotice('');
    setCode(''); setName(''); setUnit('kW'); setGroup('PEMBANGKIT'); setInputTab('PEMBANGKIT'); setAssetId('');
  }
  function startEdit(metric: Metric) {
    setKind(null); setEditing({ metric, name: metric.name, active: metric.active, role_key: metric.role_key || '' });
    setError(''); setNotice('');
    if (metric.mode === 'computed') {
      api<ExistingFormula[]>('/formulas').then(setFormulas).catch(e => setError(messageOf(e)));
    }
  }

  async function saveInput(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await api('/metrics', { method: 'POST', body: JSON.stringify({
        code: code.trim(), name: name.trim(), unit, group_name: group,
        asset_id: assetId ? Number(assetId) : null,
        input_tab_code: formTabs.length ? inputTab : null,
      }) });
      refreshCatalog(); setNotice(`Parameter ${name.trim()} berhasil ditambahkan.`); close();
    } catch (e) { setError(messageOf(e)); }
    finally { setSaving(false); }
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true); setError('');
    try {
      let confirm_disable=false;
      if(editing.metric.active&&!editing.active){
        const response=await api<{usage:{category:string;name:string}[]}>(`/metrics/${editing.metric.id}/usage`);
        if(response.usage.length){
          const details=response.usage.slice(0,20).map(x=>`• ${x.category}: ${x.name}`).join('\n');
          if(!window.confirm(`Parameter masih dipakai oleh:\n${details}\n\nNonaktifkan tetap?`))return;
          confirm_disable=true;
        }
      }
      await api(`/metrics/${editing.metric.id}`, {
        method: 'PUT', body: JSON.stringify({ name: editing.name.trim(), active: editing.active, role_key: editing.role_key.trim() || null, confirm_disable }),
      });
      refreshCatalog(); setNotice('Identitas parameter berhasil diperbarui.'); close();
    } catch (e) { setError(messageOf(e)); }
    finally { setSaving(false); }
  }

  const visible = useMemo(() => catalog.metrics.filter(metric => {
    const term = `${metric.name} ${metric.code}`.toLowerCase();
    return term.includes(search.toLowerCase()) && (!groupFilter || metric.group === groupFilter) &&
      (status==='all'||metric.active===(status==='active'));
  }), [catalog.metrics, search, groupFilter, status]);
  const paged=visible.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  const existing = editing && formulas.find(f => f.code === editing.metric.code);

  return <section className="panel parameter-manager">
    <div className="panel-head parameter-toolbar">
      <div><h3>Master Parameter</h3><p>Input pengukuran dan formula computed dikelola dari satu tempat.</p></div>
      <button className="btn primary sm" type="button" onClick={() => startCreate('input')}><Plus size={16}/> Tambah Parameter</button>
    </div>
    {notice && <div className="notice success" role="status">{notice}</div>}
    <div className="parameter-filters">
      <label className="parameter-group-filter"><SlidersHorizontal size={16}/><select aria-label="Filter kelompok parameter" value={groupFilter} onChange={e => setGroupFilter(e.target.value)}><option value="">Semua kelompok</option>{GROUPS.map(g => <option key={g} value={g}>{g}</option>)}</select></label>
    </div>
    <ListControls search={search} onSearch={setSearch} status={status} onStatus={setStatus}
      options={[{value:'active',label:'Aktif'},{value:'inactive',label:'Nonaktif'},{value:'all',label:'Semua'}]}
      page={page} onPage={setPage} count={visible.length}/>
    <div className="scroll-table"><table><thead><tr><th>Parameter</th><th>Satuan</th><th>Kelompok</th><th>Jenis</th><th>Status</th><th>Aksi</th></tr></thead><tbody>
      {paged.map(m => <tr key={m.id}><td><b>{m.name}</b><div className="mono">{m.code}</div></td><td>{m.unit}</td><td>{m.group}</td><td><span className="tag">{m.mode === 'computed' ? 'Computed' : m.mode === 'input' ? 'Input' : 'Imported'}</span></td><td><span className={'tag ' + (m.active ? 'success' : 'warning')}>{m.active ? 'Aktif' : 'Nonaktif'}</span></td><td><button type="button" className="link-btn" onClick={() => startEdit(m)}><Pencil size={13}/> Ubah</button></td></tr>)}
    </tbody></table>{!visible.length && <div className="empty">Tidak ada parameter yang cocok dengan pencarian.</div>}</div>
    <p className="parameter-hint">Parameter computed menggunakan Formula Engine V1.1 yang sama; rumus yang sudah dibuat tetap terkunci agar hasil historis terlindungi.</p>

    {open && <div className="drawer-overlay" onMouseDown={event => { if (event.target === event.currentTarget) close(); }}>
      <aside className="parameter-drawer" role="dialog" aria-modal="true" aria-label={editing ? 'Edit Parameter' : 'Tambah Parameter'}>
        <div className="drawer-heading"><div><span className="eyebrow">PENGATURAN PARAMETER</span><h3>{editing ? 'Edit Parameter' : 'Tambah Parameter'}</h3></div><button aria-label="Tutup panel" className="drawer-close" type="button" onClick={close}><X size={22}/></button></div>
        <div className="drawer-body">
          {!editing && <div className="parameter-mode-selector"><button type="button" className={kind === 'input' ? 'selected' : ''} onClick={() => startCreate('input')}><Plus size={17}/> Input</button><button type="button" className={kind === 'computed' ? 'selected' : ''} onClick={() => startCreate('computed')}><Calculator size={17}/> Computed</button></div>}
          {kind === 'input' && <form className="parameter-form" onSubmit={saveInput}>
            <label>Nama parameter<input autoFocus value={name} onChange={e => setName(e.target.value)} minLength={2} maxLength={180} required placeholder="Contoh: Daya Unit Baru"/></label>
            <label>Kode unik<input value={code} onChange={e => setCode(e.target.value.toLowerCase())} required pattern="[a-z][a-z0-9_]*" maxLength={90} placeholder="contoh: unit_baru_kw"/></label>
            <div className="parameter-form-grid"><label>Satuan<select value={unit} onChange={e => setUnit(e.target.value)}>{units.filter(u=>u.active).map(u => <option key={u.code} value={u.code}>{u.code} — {u.name}</option>)}</select></label><label>Kelompok<select value={group} onChange={e => {setGroup(e.target.value);setInputTab(formTabs.some(t=>t.code===e.target.value)?e.target.value:formTabs[0]?.code||e.target.value);}}>{GROUPS.map(g => <option key={g}>{g}</option>)}</select></label></div>
            <label>Tab di Input Beban Harian<select value={inputTab} onChange={e=>setInputTab(e.target.value)}>{formTabs.map(t=><option key={t.code} value={t.code}>{t.name}</option>)}</select></label>
            <label>Peralatan terkait<select value={assetId} onChange={e => setAssetId(e.target.value)}><option value="">Tanpa peralatan khusus</option>{catalog.assets.filter(a => a.active).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
            <p className="parameter-hint">Parameter Input otomatis muncul pada tab yang dipilih. Posisi kolom dan visibilitas bisa diatur melalui Pengaturan → Form Input.</p>
            {error && <div className="notice error" role="alert">{error}</div>}
            <button className="btn primary" disabled={saving} type="submit">{saving ? 'Menyimpan...' : 'Simpan Parameter Input'}</button>
          </form>}
          {kind === 'computed' && <><div className="parameter-hint">Rumus disusun menggunakan Formula Engine V1.1 yang sudah ada; tidak dibuat engine kedua.</div><FormulaBuilder catalog={catalog} refreshCatalog={refreshCatalog} embedded onCreated={() => { setNotice('Parameter computed berhasil ditambahkan.'); close(); }}/></>}
          {editing && <form className="parameter-form" onSubmit={saveEdit}>
            <label>Nama parameter<input autoFocus value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} required minLength={2} maxLength={180}/></label>
            <label>Kode unik<input value={editing.metric.code} disabled/></label>
            <div className="parameter-form-grid"><label>Jenis<input value={editing.metric.mode.toUpperCase()} disabled/></label><label>Satuan<input value={editing.metric.unit} disabled/></label></div>
            <label>Kunci peran (opsional)<input value={editing.role_key}
              pattern="[a-z][a-z0-9_]*(\.[a-z0-9_]+)*" maxLength={60}
              placeholder="system.load atau feeder.arus_r"
              onChange={e=>setEditing({...editing, role_key:e.target.value.toLowerCase()})}/></label>
            <p className="parameter-hint">Kunci semantik unik per unit. system.load dan system.capacity kini menentukan parameter utama; gunakan Pengaturan → Parameter utama unit.</p>
            <label className="parameter-active"><input type="checkbox" checked={editing.active} onChange={e => setEditing({ ...editing, active: e.target.checked })}/> Parameter aktif</label>
            {editing.metric.mode === 'computed' && <div className="parameter-locked"><b>Formula tersimpan (read-only)</b><code>{existing?.expression || 'Rumus bawaan / tidak ada formula kustom'}</code><small>Ekspresi tidak dapat diedit di V1.1 agar histori tetap konsisten. Revisi formula dengan versioning direncanakan untuk versi selanjutnya.</small></div>}
            {error && <div className="notice error" role="alert">{error}</div>}
            <button className="btn primary" disabled={saving} type="submit">{saving ? 'Menyimpan...' : 'Simpan Perubahan'}</button>
          </form>}
        </div>
      </aside>
    </div>}
  </section>;
}
