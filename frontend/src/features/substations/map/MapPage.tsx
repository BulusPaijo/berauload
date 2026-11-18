import {useCallback,useEffect,useMemo,useState} from 'react';
import type {CSSProperties} from 'react';
import {api,activeUnitId,num} from '../../../api';
import {fromQuery,toQuery} from '../analysis/helpers.mjs';
import type {AnalysisDefinitions} from '../analysis/types';
import type {Definitions} from '../types';
import MapCanvas from './MapCanvas';
import GarduDetail from '../detail/GarduDetail';
import {canWrite,useScope} from '../scope';
import {downloadApi} from '../../../api';
import type {MapPoint,MapResponse,TileSettings} from './types';
import {categoriesLegend,colorAndShape,quartiles,sharedURL,withinNearest} from './helpers.mjs';
import './map.css';

type Filter=Record<string,string|string[]> & {findings:string[]};
type Props={admin:boolean;canInput:boolean;onNavigate:(tab:string,stationId?:number|string)=>void};
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);
export default function MapPage({admin,onNavigate,canInput}:Props){
 const [filter,setFilter]=useState<Filter>(()=>fromQuery(location.search));
 const [defs,setDefs]=useState<AnalysisDefinitions|null>(null),[measureDefs,setMeasureDefs]=useState<Definitions|null>(null);
 const [result,setResult]=useState<MapResponse|null>(null),[tiles,setTiles]=useState<TileSettings|null>(null);
 const [selected,setSelected]=useState<MapPoint|null>(null),[error,setError]=useState('');
 const [loading,setLoading]=useState(true),[mobileFilters,setMobileFilters]=useState(false);
 const [reload,setReload]=useState(0),[cover,setCover]=useState<{stale_days:number;total:{total:number;measured:number;never:number;stale:number}}|null>(null);
 const [colorMode,setColorMode]=useState('category'),[group,setGroup]=useState('');
 const [tilesEdit,setTilesEdit]=useState(false),[tileDraft,setTileDraft]=useState<TileSettings|null>(null);
 const [locationPoint,setLocationPoint]=useState<number[]|null>(null);
 const unit=activeUnitId();
 const scope=useScope();const query=useMemo(()=>toQuery(filter),[filter]);
 const colorColumn=colorMode.startsWith('column:')?colorMode.slice(7):'';
 const set=useCallback((part:Partial<Filter>)=>setFilter(f=>({...f,...part,page:'1'})),[]);
 useEffect(()=>{
  let active=true;Promise.all([api<AnalysisDefinitions>('/substations/analysis/definitions'),
   api<Definitions>('/substations/definitions'),api<TileSettings>('/substations/map/tiles')])
   .then(([d,m,t])=>{if(active){setDefs(d);setMeasureDefs(m);setTiles(t);setTileDraft(t);
    setGroup(d.rules.find(r=>r.kind==='category')?.group_name??'');}})
   .catch(e=>{if(active)setError(msg(e))});return()=>{active=false};
 },[unit]);
 useEffect(()=>{
  const url=location.pathname+sharedURL('map',query);history.replaceState(null,'',url);
  let active=true;setLoading(true);
  api<MapResponse>('/substations/map/points?'+query+(colorColumn?'&color_column='+encodeURIComponent(colorColumn):'')).then(r=>{if(active){setResult(r);setError('');}})
   .catch(e=>{if(active)setError(msg(e))}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[query,unit,reload,colorColumn]);
 useEffect(()=>{api<typeof cover>('/substations/monitoring/coverage').then(setCover).catch(()=>{});},[unit,reload]);
 const points=result?.points??[];
 const colors=defs?.rules??[];
 const legend=categoriesLegend(colors,group);
 const numeric=colorMode.startsWith('column:')?colorMode.slice(7):null;
 const breaks=quartiles(points.map(p=>colorMode==='umur'?p.age_days:numeric?p.columns?.[numeric]?.value:null));
 const ruleByCode=useMemo(()=>new Map(colors.map(r=>[r.code,r])),[colors]);
 const pickPoint=useCallback((point:MapPoint)=>setSelected({...point,category:(()=>{const r=ruleByCode.get(point.category.code);return {code:point.category.code,name:r?.name??'Tidak dapat dinilai',color:r?.color??'#768994',marker:r?.marker??'circle'}})(),findings:(point.finding_codes??[]).map(c=>ruleByCode.get(c)).filter(Boolean).map(r=>({code:r!.code,name:r!.name,color:r!.color,marker:r!.marker??'circle',kind:r!.kind,group_name:r!.group_name}))} as MapPoint),[ruleByCode]);
 const filteredNearest=locationPoint?withinNearest(points,locationPoint[0],locationPoint[1]):[];
 function locate(){
  if(!window.isSecureContext){setError('Lokasi saya membutuhkan HTTPS atau localhost.');return;}
  if(!navigator.geolocation){setError('Geolokasi tidak didukung browser.');return;}
  navigator.geolocation.getCurrentPosition(position=>{
   setLocationPoint([position.coords.latitude,position.coords.longitude]);setError('');
  },err=>setError(err.code===1?'Izin lokasi ditolak. Aktifkan izin lokasi browser.':'Lokasi tidak tersedia. Periksa GPS atau jaringan.'),
  {enableHighAccuracy:false,timeout:12000,maximumAge:30000});
 }
 async function saveTiles(){if(!tileDraft)return;
  try{const value=await api<TileSettings>('/substations/map/tiles',{method:'PATCH',
   body:JSON.stringify({enabled:tileDraft.enabled,tile_url:tileDraft.tile_url,attribution:tileDraft.attribution})});
   setTiles(value);setTileDraft(value);setTilesEdit(false);setError('');}
  catch(e){setError(msg(e))}}
 const categoryCount=result?.summary.categories??[];
 return <div className="gardu-map-page"><header className="analysis-head"><div><div className="substation-kicker">PENGUKURAN GARDU · PETA &amp; PEMANTAUAN</div><h2>Peta Gardu Distribusi</h2><p>{defs?.units.find(u=>u.id===unit)?.name??''} · kondisi dari pengukuran terakhir tiap gardu</p></div>
  <div className="analysis-actions"><button className="btn secondary" onClick={()=>void downloadApi('/substations/monitoring/report?format=xlsx&'+query,'Laporan_Gardu.xlsx').catch(e=>setError(msg(e)))}>Unduh Excel</button><button className="btn secondary" onClick={locate}>Lokasi saya</button>{admin&&<button className="btn secondary" onClick={()=>setTilesEdit(v=>!v)}>Atur ubin</button>}{canInput&&<button className="btn primary" onClick={()=>onNavigate('input')}>+ Input pengukuran</button>}</div></header>
  {error&&<div className="notice error" role="alert">{error}<button className="btn secondary sm" onClick={()=>setReload(v=>v+1)}>Coba lagi</button></div>}
  <section className="gardu-map-kpis mk">
   <button onClick={()=>set({status:''})}><strong>{cover?.total.total??result?.total??'—'}</strong><span>gardu terdaftar</span></button>
   <button onClick={()=>set({status:'baru'})}><strong className="mk-ok">{cover?.total.measured??'—'}</strong><span>sudah diukur 90 hari terakhir</span></button>
   <button onClick={()=>set({status:'belum'})}><strong className="mk-mute">{cover?cover.total.never+cover.total.stale:'—'}</strong><span>belum diukur &gt; {cover?.stale_days??180} hari</span></button>
   {categoryCount.slice().reverse().slice(0,2).map(c=><button key={c.code} onClick={()=>set({category:c.code})}><strong style={{color:c.color}}>{c.count}</strong><span>{c.name}</span></button>)}
   {result?.summary.findings.filter(f=>f.count>0).sort((a,b)=>b.count-a.count).slice(0,2).map(f=><button key={f.code} onClick={()=>set({findings:[f.code]})}><strong style={{color:f.color}}>{f.count}</strong><span>{f.name}</span></button>)}</section>
  <button className="btn secondary gardu-map-mobile-toggle" onClick={()=>setMobileFilters(v=>!v)}>{mobileFilters?'Tutup filter':'Filter peta'}</button>
  <section className={'gardu-map-controls '+(mobileFilters?'opened':'')}>
   <input aria-label="Cari gardu" placeholder="Cari kode, nama, alamat" value={String(filter.text??'')} onChange={e=>set({text:e.target.value})}/>
   <select aria-label="Unit" value={String(filter.unit_id??'')} onChange={e=>set({unit_id:e.target.value})}><option value="">Semua unit</option>{defs?.units.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select>
   <select aria-label="Penyulang" value={String(filter.feeder_id??'')} onChange={e=>set({feeder_id:e.target.value})}><option value="">Semua penyulang</option>{defs?.feeders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select>
   <select aria-label="Sesi" value={String(filter.session??'tertinggi')} onChange={e=>set({session:e.target.value})}><option value="tertinggi">Tertinggi antar sesi</option>{defs?.sessions.map(s=><option key={s.code} value={s.code}>{s.name}</option>)}</select>
   <select aria-label="Kategori" value={String(filter.category??'')} onChange={e=>set({category:e.target.value})}><option value="">Semua kategori</option>{colors.filter(r=>r.kind==='category').map(r=><option key={r.code} value={r.code}>{r.name}</option>)}</select>
   <select aria-label="Temuan" value={filter.findings[0]??''} onChange={e=>set({findings:e.target.value?[e.target.value]:[]})}><option value="">Semua temuan</option>{colors.filter(r=>r.kind==='finding').map(r=><option key={r.code} value={r.code}>{r.name}</option>)}</select>
   <select aria-label="Warna penanda" value={colorMode} onChange={e=>setColorMode(e.target.value)}><option value="category">Warna: kategori</option><option value="umur">Warna: umur pengukuran</option>{defs?.columns.map(c=><option key={c.code} value={'column:'+c.code}>Warna: {c.name}</option>)}</select>
   {colorMode==='category'&&<select aria-label="Kelompok kategori" value={group} onChange={e=>setGroup(e.target.value)}>{[...new Set(colors.filter(r=>r.kind==='category').map(r=>r.group_name))].map(v=><option key={v} value={v}>{v}</option>)}</select>}
  </section>
  {tilesEdit&&tileDraft&&admin&&<section className="gardu-map-tile-settings"><h3>Pengaturan ubin global · hanya admin</h3><label><input type="checkbox" checked={tileDraft.enabled} onChange={e=>setTileDraft({...tileDraft,enabled:e.target.checked})}/> Tampilkan ubin</label><label>URL ubin<input value={tileDraft.tile_url} maxLength={350} onChange={e=>setTileDraft({...tileDraft,tile_url:e.target.value})}/></label><label>Atribusi<input value={tileDraft.attribution} maxLength={400} onChange={e=>setTileDraft({...tileDraft,attribution:e.target.value})}/></label><button className="btn primary" onClick={()=>void saveTiles()}>Simpan pengaturan</button></section>}
  {loading&&<p role="status" className="gardu-map-loading">Memuat titik gardu dari server…</p>}
  <div className={'gardu-map-layout '+(selected?'has-detail':'')}><section className="gardu-map-card"><MapCanvas points={points} rules={colors} colorMode={colorMode} group={group} tiles={tiles} onSelect={pickPoint} locate={locationPoint}/>
   <div className="gardu-map-legend">{colorMode==='category'?legend.map(r=><span key={r.code}><i className={'gardu-shape gardu-'+r.marker} style={{'--pin':r.color} as CSSProperties}/>{r.name}</span>):<>{breaks.map((v,i)=><span key={i}><i style={{background:['#2d72ba','#07896c','#e58a00'][i]}}/>≤ {num(v,1)}</span>)}<span>Lebih tinggi: warna merah · kosong: abu-abu</span></>}</div>
   <footer>{points.length} titik tampil · {result?.missing_coordinates??0} gardu tanpa koordinat · pengelompokan saat zoom mengecil</footer>
  </section>{selected&&<section className="gardu-map-side"><GarduDetail station={selected} canInput={canInput&&canWrite(scope,selected.unit_id)} canFollow={canInput&&canWrite(scope,selected.unit_id)} onClose={()=>setSelected(null)} onNavigate={onNavigate} onChange={()=>setReload(v=>v+1)}/></section>}
  </div>
  {!!result?.missing_coordinates&&<section className="gardu-map-missing"><h3>{result.missing_coordinates} gardu tanpa koordinat sah</h3><p>Perbaiki posisi melalui Master Gardu. Titik tanpa koordinat tidak digambar.</p><div>{result.missing.map(x=><button key={x.id} onClick={()=>onNavigate('master',x.code)}>{x.code} · {x.name}</button>)}</div>{result.missing_truncated&&<small>Daftar dibatasi 100 gardu; gunakan Master Gardu untuk melihat sisanya.</small>}</section>}
  {!!filteredNearest.length&&<section className="gardu-map-missing"><h3>Terdekat dari lokasi saya</h3><div>{filteredNearest.map(p=><button key={p.id} onClick={()=>pickPoint(p)}>{p.code} · {num(p.distance_km,2)} km</button>)}</div><small>Jarak garis lurus, bukan rute perjalanan.</small></section>}
 </div>;
}
