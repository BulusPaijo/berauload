import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Pencil, Plus, X } from 'lucide-react';
import { api, type Asset, type Catalog } from '../../api';
import '../parameters/parameters.css';
import './assets.css';
import ListControls,{PAGE_SIZE} from '../../shared/ListControls';
import type {EquipmentKind} from '../../api';

const describe = (error: unknown) => error instanceof Error ? error.message : String(error);
const toCode = (label: string) => label.toLowerCase().normalize('NFKD')
  .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_')
  .replace(/^_+|_+$/g, '').replace(/^[^a-z]+/, '');

export default function AssetManager({ catalog, refreshCatalog }: {
  catalog: Catalog; refreshCatalog: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [kind, setKind] = useState('pembangkit');
  const [active, setActive] = useState(true);
  const [customCode, setCustomCode] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [status,setStatus] = useState('active');
  const [page,setPage] = useState(1);
  const [kinds,setKinds] = useState<EquipmentKind[]>([]);
  const kindLabel=(code:string)=>kinds.find(x=>x.code===code)?.name||code;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(()=>{api<EquipmentKind[]>('/equipment-kinds').then(setKinds).catch(e=>setError(describe(e)))},[]);

  useEffect(() => {
    if (!open) return;
    const keyHandler = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) setOpen(false);
    };
    window.addEventListener('keydown', keyHandler);
    return () => window.removeEventListener('keydown', keyHandler);
  }, [open, busy]);

  const shown = useMemo(() => catalog.assets.filter(asset => {
    const matchName = `${asset.name} ${asset.code}`.toLowerCase().includes(search.toLowerCase());
    return matchName && (!filter || asset.kind === filter) && (status === 'all' || asset.active === (status === 'active'));
  }), [catalog.assets, search, filter, status]);

  const paged=shown.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
  function add() {
    setEditing(null); setName(''); setCode('');
    setActive(true); setCustomCode(false); setError(''); setNotice(''); setKind(kinds.find(k=>k.active)?.code||''); setOpen(true);
  }

  function edit(asset: Asset) {
    setEditing(asset); setName(asset.name); setCode(asset.code); setKind(asset.kind);
    setActive(asset.active); setCustomCode(true); setError(''); setNotice(''); setOpen(true);
  }

  function updateName(value: string) {
    setName(value);
    if (!editing && !customCode) setCode(toCode(value));
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      if (editing) {
        await api(`/assets/${editing.id}`, {
          method: 'PUT', body: JSON.stringify({ name: name.trim(), active }),
        });
      } else {
        await api('/assets', {
          method: 'POST', body: JSON.stringify({ code: code.trim(), name: name.trim(), kind }),
        });
      }
      refreshCatalog(); setNotice(editing ? 'Peralatan berhasil diperbarui.' : 'Peralatan berhasil ditambahkan.');
      setOpen(false);
    } catch (e) { setError(describe(e)); }
    finally { setBusy(false); }
  }

  return <section className="panel asset-manager">
    <div className="panel-head parameter-toolbar">
      <div><h3>Master Peralatan</h3><p>Kelola identitas peralatan tanpa mengubah pengukuran historis.</p></div>
      <button type="button" className="btn primary sm" onClick={add}><Plus size={16}/> Tambah Peralatan</button>
    </div>
    {notice && <div className="notice success" role="status">{notice}</div>}
    <div className="parameter-filters">
      <label className="parameter-group-filter"><select aria-label="Jenis peralatan" value={filter} onChange={e => setFilter(e.target.value)}>
        <option value="">Semua jenis</option>{[...new Set([...kinds.map(k=>k.code),...catalog.assets.map(a=>a.kind)])].map(k=>
          <option key={k} value={k}>{kindLabel(k)}</option>)}
      </select></label>
    </div>
    <ListControls search={search} onSearch={setSearch} status={status} onStatus={setStatus}
      options={[{value:'active',label:'Aktif'},{value:'inactive',label:'Nonaktif'},{value:'all',label:'Semua'}]}
      page={page} onPage={setPage} count={shown.length}/>
    <div className="scroll-table"><table><thead><tr><th>Peralatan</th><th>Jenis</th><th>Parameter</th><th>Status</th><th>Aksi</th></tr></thead><tbody>
      {paged.map(asset => <tr key={asset.id}>
        <td><b>{asset.name}</b><div className="mono">{asset.code}</div></td>
        <td>{kindLabel(asset.kind)}</td>
        <td>{catalog.metrics.filter(m => m.asset_id === asset.id).length}</td>
        <td><span className={'tag ' + (asset.active ? 'success' : 'warning')}>{asset.active ? 'Aktif' : 'Nonaktif'}</span></td>
        <td><button className="link-btn" type="button" onClick={() => edit(asset)}><Pencil size={13}/> Ubah</button></td>
      </tr>)}
    </tbody></table>{shown.length === 0 && <div className="empty">Peralatan tidak ditemukan.</div>}</div>
    <p className="parameter-hint">Kode dan jenis peralatan lama dikunci. Parameter yang terkait tetap menyimpan identitas peralatan meskipun statusnya nonaktif.</p>
    {open && <div className="drawer-overlay" onMouseDown={e => { if (e.target === e.currentTarget && !busy) setOpen(false); }}>
      <aside className="parameter-drawer" role="dialog" aria-modal="true" aria-label={editing ? 'Ubah Peralatan' : 'Tambah Peralatan'}>
        <div className="drawer-heading"><div><span className="eyebrow">MASTER PERALATAN</span><h3>{editing ? 'Ubah Peralatan' : 'Tambah Peralatan'}</h3></div>
          <button type="button" className="drawer-close" aria-label="Tutup panel" disabled={busy} onClick={() => setOpen(false)}><X size={22}/></button>
        </div>
        <div className="drawer-body"><form className="parameter-form" onSubmit={submit}>
          <label>Nama peralatan<input autoFocus required minLength={2} maxLength={180} value={name} onChange={e => updateName(e.target.value)} placeholder="Contoh: PLTU Unit 5"/></label>
          <label>Kode unik<input required disabled={Boolean(editing)} minLength={2} maxLength={80} pattern="[a-z][a-z0-9_]*" value={code} onChange={e => { setCode(e.target.value.toLowerCase()); setCustomCode(true); }} placeholder="Contoh: pltu_unit_5"/></label>
          <label>Jenis peralatan<select disabled={Boolean(editing)} required value={kind} onChange={e => setKind(e.target.value)}>
            {!kinds.some(x=>x.code===kind)&&<option value={kind}>{kind}</option>}
            {kinds.filter(k=>k.active||k.code===kind).map(k=><option key={k.code} value={k.code}>{k.name}</option>)}
          </select></label>
          {editing && <label className="parameter-active"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)}/> Peralatan aktif</label>}
          <p className="parameter-hint">Kapasitas nominal tidak diinput di master V1.1.3. Daya Mampu Sistem tetap berasal dari kolom H rekap.</p>
          {error && <div className="notice error" role="alert">{error}</div>}
          <button className="btn primary" disabled={busy} type="submit">{busy ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah Peralatan'}</button>
        </form></div>
      </aside>
    </div>}
  </section>;
}
