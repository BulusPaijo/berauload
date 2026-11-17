import {createContext,useContext,useEffect,useMemo,useState} from 'react';
import type {ReactNode} from 'react';
import {readCachedBrand,cacheBrand,metadataFor} from './branding.mjs';
import type {Brand} from './branding.mjs';

type BrandingState = {branding:Brand;updateBranding:(next:Brand)=>void};
const Context=createContext<BrandingState|null>(null);

export function BrandingProvider({children}:{children:ReactNode}){
 const [branding,setBranding]=useState<Brand>(()=>readCachedBrand(typeof localStorage==='undefined'?null:localStorage));
 const updateBranding=(next:Brand)=>{setBranding(next);cacheBrand(typeof localStorage==='undefined'?null:localStorage,next)};
 useEffect(()=>{
  let active=true;
  fetch('/api/branding',{credentials:'same-origin',cache:'no-cache'}).then(r=>{
   if(!r.ok)throw new Error('Branding tidak tersedia');return r.json();
  }).then(data=>{if(active)updateBranding(data)}).catch(()=>{});
  return()=>{active=false};
 },[]);
 useEffect(()=>{
  const meta=metadataFor(branding);
  document.title=meta.title;
  document.documentElement.style.setProperty('--brand-primary',branding.color_primary);
  document.documentElement.style.setProperty('--brand-accent',branding.color_accent);
  document.documentElement.style.setProperty('--brand-highlight',branding.color_accent==='#03A7A4'?'#4cf1c1':branding.color_accent);
  document.documentElement.style.setProperty('--brand-nav',branding.color_primary==='#087E89'?'#106574':branding.color_primary);
  const icon=document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if(icon){icon.href=meta.favicon;icon.type=branding.has_favicon?'image/png':'image/svg+xml'}
  const theme=document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if(theme)theme.content=meta.theme;
  const description=document.querySelector<HTMLMetaElement>('meta[name="description"]');
  if(description)description.content=meta.description;
 },[branding]);
 const value=useMemo(()=>({branding,updateBranding}),[branding]);
 return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useBranding(){const value=useContext(Context);if(!value)throw new Error('BrandingProvider belum terpasang');return value}
