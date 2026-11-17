import {useEffect,useState} from 'react';
import type {CSSProperties} from 'react';
import {api,apiFetch} from '../../api';
import {BRAND_FIELDS,BRAND_LIMITS,contrastWhite} from './branding.mjs';
import type {Brand} from './branding.mjs';
import {useBranding} from './BrandingContext';
import './branding.css';

const labels:Record<string,string>={app_name:'Nama aplikasi',app_short_name:'Nama pendek',tagline:'Tagline',
 login_eyebrow:'Label bagian atas login',login_welcome:'Pesan selamat datang',
 login_description:'Deskripsi login',login_button_text:'Teks tombol login',
 login_footnote:'Catatan kaki login',organization_name:'Nama organisasi',footer_text:'Teks footer',
 color_primary:'Warna utama',color_accent:'Warna aksen'};
const imageMessages:Record<number,string>={401:'Sesi telah berakhir, silakan login kembali',
 403:'Hanya admin yang boleh mengubah branding',422:'Berkas ditolak: periksa format, ukuran, dan dimensi'};
export default function BrandingSettings(){
 const {branding,updateBranding}=useBranding();
 const [draft,setDraft]=useState<Brand>(branding),[busy,setBusy]=useState(false);
 const [error,setError]=useState(''),[message,setMessage]=useState('');
 const [images,setImages]=useState<Record<string,File|null>>({logo:null,favicon:null});
 const [previews,setPreviews]=useState<Record<string,string>>({});
 useEffect(()=>setDraft(branding),[branding]);
 useEffect(()=>()=>{Object.values(previews).forEach(url=>URL.revokeObjectURL(url))},[previews]);
 const valid=contrastWhite(draft.color_primary)>=4.5;
 const setField=(field:string,value:string)=>setDraft(prev=>({...prev,[field]:value}));
 const selectFile=(kind:string,file:File|null)=>{
  setImages(p=>({...p,[kind]:file}));
  setPreviews(p=>{const next={...p};delete next[kind];if(file)next[kind]=URL.createObjectURL(file);return next});
 };
 const refresh=(value:Brand)=>{updateBranding(value);setMessage('Branding berhasil diperbarui. Pengguna lain melihatnya setelah reload.')};
 async function save(){
  if(!valid){setError('Warna utama harus memiliki kontras minimal 4.5:1 terhadap teks putih');return}
  setBusy(true);setError('');setMessage('');
  try{const payload=Object.fromEntries(BRAND_FIELDS.map(key=>[key,(draft as unknown as Record<string,string>)[key]]));
   const result=await api<Brand>('/branding',{method:'PUT',body:JSON.stringify(payload)});refresh(result);
  }catch(e){setError(String(e instanceof Error?e.message:e))}finally{setBusy(false)}
 }
 async function upload(kind:'logo'|'favicon'){
  const file=images[kind];if(!file)return;
  setBusy(true);setError('');setMessage('');
  try{const form=new FormData();form.append('file',file);
   const response=await apiFetch(`/api/branding/${kind}`,{method:'POST',body:form});
   if(!response.ok)throw new Error(imageMessages[response.status]||`Unggahan gagal: HTTP ${response.status}`);
   refresh(await response.json());selectFile(kind,null);
  }catch(e){setError(String(e instanceof Error?e.message:e))}finally{setBusy(false)}
 }
 async function remove(kind:'logo'|'favicon'){
  if(!window.confirm(`Kembalikan ${kind} ke ikon bawaan?`))return;
  setBusy(true);setError('');
  try{refresh(await api<Brand>(`/branding/${kind}`,{method:'DELETE'}))}
  catch(e){setError(String(e instanceof Error?e.message:e))}finally{setBusy(false)}
 }
 async function reset(){
  if(!window.confirm('Kembalikan SEMUA branding, termasuk logo dan favicon, ke bawaan?'))return;
  setBusy(true);setError('');
  try{refresh(await api<Brand>('/branding/reset',{method:'POST'}))}
  catch(e){setError(String(e instanceof Error?e.message:e))}finally{setBusy(false)}
 }
 return <section className="panel branding-settings"><h3>Branding Aplikasi</h3>
  <p className="muted">Identitas tampilan berlaku untuk semua unit. Kode internal, template lama, cookie, dan database tidak berubah.</p>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {message&&<div className="notice success" role="status">{message}</div>}
  <div className="branding-fields">{BRAND_FIELDS.filter(k=>!k.startsWith('color_')).map(key=>{
   const val=(draft as unknown as Record<string,string>)[key]??'';
   return <label key={key}>{labels[key]}<input value={val} maxLength={BRAND_LIMITS[key]}
    onChange={e=>setField(key,e.target.value)}/><small>{val.length}/{BRAND_LIMITS[key]}</small></label>
  })}</div>
  <div className="branding-colors">{(['color_primary','color_accent'] as const).map(key=><label key={key}>{labels[key]}
   <input type="color" value={draft[key]} onChange={e=>setField(key,e.target.value)}/>
   <input aria-label={`${labels[key]} dalam hex`} value={draft[key]} onChange={e=>setField(key,e.target.value)} maxLength={7}/>
  </label>)}</div>
  <p className={valid?'muted':'notice error'}>Kontras tombol terhadap putih: {contrastWhite(draft.color_primary).toFixed(2)}:1 (minimal 4.5:1).</p>
  <div className="branding-images">{(['logo','favicon'] as const).map(kind=><div key={kind}>
   <h4>{kind==='logo'?'Logo':'Favicon'}</h4>
   <p className="muted">{kind==='logo'?'PNG/JPEG/WebP · 512 KB · maksimal 1024 px':'PNG/ICO/WebP · 128 KB · maksimal 256 px'}</p>
   {previews[kind]&&<img src={previews[kind]} alt={`Pratinjau ${kind}`} width="75" height="75"/>}
   <input type="file" accept={kind==='logo'?'image/png,image/jpeg,image/webp':'image/png,image/x-icon,image/webp'}
    aria-label={`Unggah ${kind}`} onChange={e=>selectFile(kind,e.target.files?.[0]??null)}/>
   <div className="toolbar-actions"><button className="btn secondary sm" disabled={busy||!images[kind]} onClick={()=>upload(kind)}>Unggah {kind}</button>
   <button className="btn secondary sm" disabled={busy} onClick={()=>remove(kind)}>Hapus</button></div>
  </div>)}</div>
  <div className="branding-preview" style={{'--brand-primary':draft.color_primary,'--brand-accent':draft.color_accent} as CSSProperties}>
   <div><b>Pratinjau kartu login</b>{(previews.logo||branding.has_logo)&&<img width="64" height="64" style={{objectFit:'contain'}} alt={draft.app_name} src={previews.logo||`/api/branding/logo?v=${branding.logo_version}`}/>}<span>{draft.login_eyebrow}</span><h3>{draft.login_welcome} {draft.app_name}</h3>
    <p>{draft.login_description}</p><button className="btn primary" disabled>{draft.login_button_text}</button><small>{draft.login_footnote}</small></div>
   <div><b>Pratinjau sidebar</b>{(previews.logo||branding.has_logo)&&<img width="48" height="48" style={{objectFit:'contain'}} alt={draft.app_name} src={previews.logo||`/api/branding/logo?v=${branding.logo_version}`}/>}<span>{draft.app_short_name}</span><small>{draft.tagline}</small></div>
  </div>
  <div className="toolbar-actions"><button className="btn primary" disabled={busy||!valid} onClick={save}>Simpan Branding</button>
   <button className="btn secondary" disabled={busy} onClick={reset}>Kembalikan semua ke bawaan</button></div>
 </section>;
}
