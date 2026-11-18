import {Save,Trash2} from 'lucide-react';

export type Template={id:number;name:string;shared:boolean;version:number;owner_id:number|null;spec:unknown;warnings:string[]};
type Props={templates:Template[];selected:string;name:string;shared:boolean;admin:boolean;userId:number;busy:boolean;valid:boolean;
 onSelect:(id:string)=>void;onName:(v:string)=>void;onShared:(v:boolean)=>void;onSave:()=>void;onUpdate:()=>void;onArchive:()=>void};
export default function ExportTemplates(p:Props){
 const current=p.templates.find(t=>String(t.id)===p.selected);
 const canEdit=!!current&&(current.shared?p.admin:current.owner_id===p.userId);
 return <section className="panel export-section"><h3>Template export</h3>
  <div className="export-fields">
   <label>Template tersimpan<select value={p.selected} onChange={e=>p.onSelect(e.target.value)}><option value="">Pilih template</option>
    {p.templates.map(t=><option key={t.id} value={t.id}>{t.name} · {t.shared?'Bersama':'Pribadi'}</option>)}</select></label>
   <label>Nama template<input value={p.name} maxLength={150} onChange={e=>p.onName(e.target.value)}/></label>
   <label>Jenis<select value={p.shared?'shared':'personal'} onChange={e=>p.onShared(e.target.value==='shared')}><option value="personal">Pribadi</option>{p.admin&&<option value="shared">Bersama (admin)</option>}</select></label>
  </div>
  {!!current?.warnings.length&&<div className="notice info" role="status">Kolom berikut sudah tidak tersedia dan dilewati: {current.warnings.join(', ')}</div>}
  <div className="export-actions">
   <button className="btn secondary" disabled={p.busy||!p.valid||p.name.trim().length<3} onClick={p.onSave}><Save size={16}/> Simpan sebagai template baru</button>
   <button className="btn secondary" disabled={p.busy||!p.valid||!canEdit} onClick={p.onUpdate}><Save size={16}/> Perbarui template terpilih</button>
   <button className="btn secondary" disabled={p.busy||!canEdit} onClick={p.onArchive}><Trash2 size={16}/> Arsipkan</button>
  </div>
  <p className="muted small">Mengarsipkan tidak menghapus data pengukuran.</p>
 </section>;
}
