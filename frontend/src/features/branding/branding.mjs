// Deliberate mirror of backend/app/modules/branding/defaults.py; equality regression test.
export const BRAND_DEFAULTS = Object.freeze({
  app_name:'BerauLoad', app_short_name:'BerauLoad', tagline:'Sistem Kelistrikan Berau',
  login_eyebrow:'SISTEM KELISTRIKAN BERAU', login_welcome:'Selamat datang di',
  login_description:'Pencatatan operasional, monitoring dan analisis beban dalam satu platform.',
  login_button_text:'Masuk ke BerauLoad', login_footnote:'Akses khusus untuk personel yang berwenang.',
  organization_name:'', footer_text:'Data operasional internal',
  color_primary:'#087E89', color_accent:'#03A7A4',
});
export const BRAND_FIELDS = Object.keys(BRAND_DEFAULTS);
export const BRAND_LIMITS = Object.freeze({app_name:40,app_short_name:20,tagline:60,
  login_eyebrow:80,login_welcome:80,login_description:200,login_button_text:60,
  login_footnote:120,organization_name:100,footer_text:120});
export const STORAGE_KEY = 'berauload_public_branding_v1';
export function normalizeBrand(data){
  const out={};
  for(const k of BRAND_FIELDS)out[k]=typeof data?.[k]==='string'?data[k]:BRAND_DEFAULTS[k];
  for(const k of ['logo_version','favicon_version'])out[k]=Number.isSafeInteger(data?.[k])&&data[k]>=0?data[k]:0;
  for(const k of ['has_logo','has_favicon'])out[k]=data?.[k]===true;
  return out;
}
export function readCachedBrand(storage){
  try{const raw=storage?.getItem(STORAGE_KEY);return raw?normalizeBrand(JSON.parse(raw)):normalizeBrand(null)}
  catch{return normalizeBrand(null)}
}
export function cacheBrand(storage,value){
  try{storage?.setItem(STORAGE_KEY,JSON.stringify(normalizeBrand(value)));return true}
  catch{return false}
}
export function safeBrandSlug(input){return (String(input||'').replace(/[^A-Za-z0-9_]+/g,'_').replace(/^_+|_+$/g,'').slice(0,50))||'BerauLoad'}
export function contrastWhite(color){
  if(!/^#[0-9a-fA-F]{6}$/.test(color))return 0;
  const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255);
  const linear=rgb.map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
  return 1.05/(.2126*linear[0]+.7152*linear[1]+.0722*linear[2]+.05);
}
export function metadataFor(branding){
  return {title:`${branding.app_name} — ${branding.tagline}`, description:`${branding.app_name} — ${branding.login_description}`,
    favicon:`/api/branding/favicon?v=${branding.favicon_version}`,theme:branding.color_primary};
}
