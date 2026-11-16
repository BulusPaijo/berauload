import UnitMetricOptions from '../unit-references/UnitMetricOptions';
import { useEffect, useMemo, useState } from 'react';
import { Calculator, CheckCircle2, FlaskConical, LockKeyhole, Plus } from 'lucide-react';
import { api, isoWita, type Catalog } from '../../api';
import {useUnitMetricReferences,metricsForSelection} from '../unit-references/useUnitMetricReferences';
import type {UnitItem} from '../units/UnitManager';
import './formulas.css';

type SavedFormula = { code: string; name: string; unit: string; expression: string; version: number; active: boolean };
type Preview = { valid: boolean; result: number | null; missing: string[]; references: string[]; warning?: string };
type Preset = 'SUM' | 'AVG' | 'MIN' | 'MAX' | 'ADD' | 'SUB' | 'MUL' | 'DIV' | 'IF' | 'CUSTOM';
const OPERATIONS: { value: Preset; label: string }[] = [
  { value: 'SUM', label: 'Jumlah (SUM)' }, { value: 'AVG', label: 'Rata-rata (AVG)' },
  { value: 'MIN', label: 'Minimum (MIN)' }, { value: 'MAX', label: 'Maksimum (MAX)' },
  { value: 'ADD', label: 'Tambah (+)' }, { value: 'SUB', label: 'Kurang (−)' },
  { value: 'MUL', label: 'Kali (×)' }, { value: 'DIV', label: 'Bagi (÷)' },
  { value: 'IF', label: 'Kondisi (IF)' }, { value: 'CUSTOM', label: 'Formula Excel-like' },
];
const GROUPS = ['REKAP', 'PEMBANGKIT', 'KUALITAS', 'FEEDER', 'REKAP_LAIN'];
const cleanNumber = (value: string) => value.trim() === '' ? '0' : String(Number(value));

function visualExpression(preset: Preset, items: string[], comparison: string, threshold: string, yes: string, no: string) {
  const chosen = items.filter(Boolean);
  if (!chosen.length) return '';
  if (preset === 'CUSTOM') return '';
  if (preset === 'IF') return `IF(${chosen[0]} ${comparison} ${cleanNumber(threshold)}, ${cleanNumber(yes)}, ${cleanNumber(no)})`;
  if (['SUM', 'AVG', 'MIN', 'MAX'].includes(preset)) return `${preset}(${chosen.join(', ')})`;
  if (chosen.length < 2) return '';
  const op = { ADD: '+', SUB: '-', MUL: '*', DIV: '/' }[preset as 'ADD' | 'SUB' | 'MUL' | 'DIV'];
  return `(${chosen[0]} ${op} ${chosen[1]})`;
}

export default function FormulaBuilder({ catalog, refreshCatalog, embedded = false, onCreated }: { catalog: Catalog; refreshCatalog: () => void; embedded?: boolean; onCreated?: () => void }) {
  const referencesAll=useUnitMetricReferences();
  const metrics = metricsForSelection(referencesAll,catalog.metrics).filter(m => m.active);
  const [roleChoice,setRoleChoice]=useState('system.load');
  const [checkDay,setCheckDay]=useState(isoWita());
  const [checkHour,setCheckHour]=useState(0);
  const [coverage,setCoverage]=useState<{code:string;label:string;complete:boolean}[]|null>(null);
  const [units, setUnits] = useState<UnitItem[]>([]);
  useEffect(()=>{api<UnitItem[]>('/units').then(setUnits).catch(()=>{});},[]);
  const [saved, setSaved] = useState<SavedFormula[]>([]);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [unit, setUnit] = useState('kW');
  const [group, setGroup] = useState('REKAP');
  const [asset, setAsset] = useState('');
  const [preset, setPreset] = useState<Preset>('SUM');
  const [items, setItems] = useState<string[]>(['', '', '']);
  const [comparison, setComparison] = useState('>');
  const [threshold, setThreshold] = useState('0');
  const [yes, setYes] = useState('1');
  const [no, setNo] = useState('0');
  const [custom, setCustom] = useState('');
  const [samples, setSamples] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const expression = preset === 'CUSTOM' ? custom : visualExpression(preset, items, comparison, threshold, yes, no);
  const references = useMemo(() => metrics.filter(m => new RegExp(`\\b${m.code}\\b`).test(expression)), [metrics, expression]);

  function load() { api<SavedFormula[]>('/formulas').then(setSaved).catch(e => setError(String(e))); }
  async function checkCompleteness(){
    try{
      const result=await api<{formulas:{code:string;label:string;complete:boolean}[]}>(
        `/formulas/completeness?day=${checkDay}&hour=${checkHour}`);
      setCoverage(result.formulas);setError('');
    }catch(e){setError(String(e))}
  }
  useEffect(() => { load(); }, []);
  function setItem(index: number, value: string) {
    setItems(old => old.map((v, i) => i === index ? value : v));
    setPreview(null);
  }
  function prepareSamples() {
    const parsed: Record<string, number | null> = {};
    references.forEach(ref => { parsed[ref.code] = samples[ref.code]?.trim() ? Number(samples[ref.code]) : null; });
    return parsed;
  }
  async function test() {
    setError(''); setMessage(''); setPreview(null);
    if (!expression.trim()) { setError('Pilih parameter dan operasi terlebih dahulu.'); return; }
    setBusy(true);
    try { setPreview(await api<Preview>('/formulas/preview', { method: 'POST', body: JSON.stringify({ expression, unit, samples: prepareSamples() }) })); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function create() {
    setError(''); setMessage(''); setBusy(true);
    try {
      const result = await api<{ code: string; note: string }>('/formulas', {
        method: 'POST', body: JSON.stringify({ code, name, unit, group_name: group, asset_id: asset ? Number(asset) : null, expression }),
      });
      setMessage(`Rumus ${result.code} berhasil dibuat. ${result.note}`);
      setCode(''); setName(''); setPreview(null); refreshCatalog(); load(); onCreated?.();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return <section className="formula-section">
    {!embedded && <div className="formula-heading"><div><span className="eyebrow">FORMULA ENGINE V1.1</span><h3><Calculator size={20}/> Formula Builder</h3><p>Buat parameter hasil hitung melalui UI. Tidak memerlukan kode Python.</p></div></div>}
    <div className="formula-layout">
      <div className="formula-card">
        <h4>1. Identitas hasil perhitungan</h4>
        <div className="formula-grid">
          <label>Kode unik<input value={code} onChange={e => setCode(e.target.value.toLowerCase())} placeholder="contoh: cadangan_daya_kw"/></label>
          <label>Nama parameter<input value={name} onChange={e => setName(e.target.value)} placeholder="Cadangan Daya Sistem"/></label>
          <label>Satuan hasil<select value={unit} onChange={e => { setUnit(e.target.value); setPreview(null); }}>{units.filter(u=>u.active).map(v => <option key={v.code} value={v.code}>{v.code} — {v.name}</option>)}</select></label>
          <label>Kelompok<select value={group} onChange={e => setGroup(e.target.value)}>{GROUPS.map(v => <option key={v}>{v}</option>)}</select></label>
          <label className="span-wide">Peralatan<select value={asset} onChange={e => setAsset(e.target.value)}><option value="">Tanpa peralatan khusus</option>{catalog.assets.filter(x => x.active).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
        </div>
      </div>
      <div className="formula-card">
        <h4>2. Susun rumus</h4>
        <label>Jenis operasi<select value={preset} onChange={e => { setPreset(e.target.value as Preset); setPreview(null); }}>{OPERATIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
        {preset === 'CUSTOM' ? <label>Rumus Excel-like<textarea value={custom} onChange={e => { setCustom(e.target.value); setPreview(null); }} rows={4} placeholder={`IF(${catalog.roles?.['system.load']||'parameter_beban'} > ${catalog.roles?.['system.capacity']||'parameter_daya_mampu'}, 1, 0)`}/></label> : <>
          <div className="formula-grid">
            {Array.from({ length: ['ADD','SUB','MUL','DIV'].includes(preset) ? 2 : preset === 'IF' ? 1 : Math.max(3,items.length) }, (_, index) =>
              <label key={index}>Parameter {index + 1}<select value={items[index]} onChange={e => setItem(index, e.target.value)}><option value="">Pilih parameter</option><UnitMetricOptions metrics={metrics}/></select></label>)}
          </div>
          {['SUM','AVG','MIN','MAX'].includes(preset)&&<div className="formula-operands">
            <button type="button" className="btn secondary sm" onClick={()=>setItems(old=>[...old,''])}>Tambah operand</button>
            <select aria-label="Peran parameter unit bawah" value={roleChoice} onChange={e=>setRoleChoice(e.target.value)}>
              {[...new Set(referencesAll.filter(m=>m.source&&m.role_key).map(m=>m.role_key!))].map(role=><option key={role} value={role}>{role}</option>)}
            </select>
            <button type="button" className="btn secondary sm" onClick={()=>setItems(referencesAll.filter(m=>m.source&&m.role_key===roleChoice).map(m=>m.code))}>Tambah parameter berperan sama dari unit di bawah</button>
            <small>Periksa agar beban unit bawah tidak terhitung dua kali jika sudah termasuk dalam pengukuran unit atas. Daftar operand yang disimpan selalu eksplisit.</small>
          </div>}
          {preset === 'IF' && <div className="formula-grid">
            <label>Kondisi<select value={comparison} onChange={e => setComparison(e.target.value)}>{['>','>=','<','<=','==','!='].map(v => <option key={v}>{v}</option>)}</select></label>
            <label>Nilai batas<input inputMode="decimal" value={threshold} onChange={e => setThreshold(e.target.value)}/></label>
            <label>Hasil jika benar<input inputMode="decimal" value={yes} onChange={e => setYes(e.target.value)}/></label>
            <label>Hasil jika salah<input inputMode="decimal" value={no} onChange={e => setNo(e.target.value)}/></label>
          </div>}
        </>}
        <div className="formula-expression"><small>Rumus yang akan disimpan</small><code>{expression || 'Pilih minimal satu parameter'}</code></div>
      </div>
      <div className="formula-card">
        <h4>3. Uji dengan angka contoh</h4>
        {!references.length && <p className="muted">Pilih parameter untuk menampilkan kolom simulasi.</p>}
        <div className="formula-grid">{references.map(m => <label key={m.code}>{'label' in m ? String(m.label) : m.name} ({m.unit})<input type="number" value={samples[m.code] || ''} onChange={e => { setSamples(old => ({ ...old, [m.code]: e.target.value })); setPreview(null); }} placeholder="Isi nilai uji"/></label>)}</div>
        <button type="button" disabled={busy || !expression} className="btn secondary" onClick={test}><FlaskConical size={16}/> Uji Rumus</button>
        {preview && <div className="formula-preview"><b>{preview.result === null ? 'Belum dapat dihitung' : `${preview.result.toLocaleString('id-ID')} ${unit}`}</b><small>{preview.missing.length ? `Data kosong: ${preview.missing.join(', ')}` : preview.warning || 'Validasi berhasil'}</small></div>}
        {error && <div className="notice error">{error}</div>}
        {message && <div className="notice success"><CheckCircle2 size={16}/>{message}</div>}
        <button type="button" className="btn primary" disabled={busy || !code || !name || !expression} onClick={create}><Plus size={16}/> Aktifkan Parameter Computed</button>
        <p className="formula-footnote"><LockKeyhole size={14}/> Rumus V1.1 tidak dapat diedit setelah disimpan. Perubahan rumus akan menggunakan versioning pada pengembangan selanjutnya. Histori tidak dihitung ulang.</p>
      </div>
    </div>
    {!embedded && <div className="formula-card"><h4>Parameter Computed Buatan Admin</h4>
      {!saved.length ? <p className="muted">Belum ada rumus baru. Rumus rekap bawaan V1 tetap berjalan dan tidak diubah.</p> :
        <div className="scroll-table"><table><thead><tr><th>Parameter</th><th>Rumus</th><th>Versi</th><th>Status</th></tr></thead><tbody>{saved.map(f => <tr key={f.code}><td><b>{f.name}</b><div className="mono">{f.code}</div></td><td className="mono">{f.expression}</td><td>{f.version}</td><td>{f.active ? 'Aktif' : 'Nonaktif'}</td></tr>)}</tbody></table></div>}
      <div className="formula-coverage"><h4>Kelengkapan operand per jam (WITA)</h4>
        <p className="muted small">Perhitungan memerlukan seluruh operand eksplisit. Sumber kosong menghasilkan NULL, bukan penjumlahan parsial; 0 tetap nilai sah.</p>
        <label>Tanggal<input type="date" value={checkDay} onChange={e=>{setCheckDay(e.target.value);setCoverage(null)}}/></label>
        <label>Jam<select value={checkHour} onChange={e=>{setCheckHour(Number(e.target.value));setCoverage(null)}}>
          {Array.from({length:24},(_,hour)=><option value={hour} key={hour}>{String(hour).padStart(2,'0')}:00</option>)}
        </select></label>
        <button type="button" className="btn secondary sm" onClick={checkCompleteness}>Periksa kelengkapan</button>
        {coverage?.map(row=><p key={row.code}><b>{row.code}</b>: {row.label} {row.complete?'✓':''}</p>)}
      </div>
    </div>}
  </section>;
}
