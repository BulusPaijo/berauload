import test from 'node:test';
import assert from 'node:assert/strict';
import {BRAND_DEFAULTS,normalizeBrand,readCachedBrand,cacheBrand,safeBrandSlug,
 contrastWhite,metadataFor,STORAGE_KEY} from '../src/features/branding/branding.mjs';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const serverDefault=readFileSync(fileURLToPath(new URL('../../backend/app/modules/branding/defaults.py',import.meta.url)),'utf8');
test('default public branding mirrored with backend authoritative defaults',()=>{
 for(const [k,v] of Object.entries(BRAND_DEFAULTS)){
  assert.ok(serverDefault.includes(`'${k}': '${v}'`),`${k} default differs`);
 }
 const b=normalizeBrand(null);
 assert.equal(b.app_name,'BerauLoad');
 assert.equal(metadataFor(b).title,'BerauLoad — Sistem Kelistrikan Berau');
 assert.equal(metadataFor(b).favicon,'/api/branding/favicon?v=0');
});
test('slug/contrast and branding metadata',()=>{
 assert.equal(safeBrandSlug('A/Bä@=+ Z'), 'A_B_Z');
 assert.equal(safeBrandSlug('=*'),'BerauLoad');
 assert.ok(contrastWhite('#087E89')>=4.5);
 assert.ok(contrastWhite('#FFFFFF')<4.5);
 assert.equal(contrastWhite('purple'),0);
 const b=normalizeBrand({...BRAND_DEFAULTS,app_name:'Sistem Beban',tagline:'UP3',favicon_version:8});
 assert.equal(metadataFor(b).title,'Sistem Beban — UP3');
 assert.equal(metadataFor(b).favicon,'/api/branding/favicon?v=8');
});
test('storage absent/broken/disabled harmless and never stores credentials',()=>{
 const mem=new Map();const store={getItem:k=>mem.get(k)||null,setItem:(k,v)=>mem.set(k,v)};
 assert.equal(readCachedBrand(null).app_name,'BerauLoad');
 mem.set(STORAGE_KEY,'{broken');assert.equal(readCachedBrand(store).app_name,'BerauLoad');
 const b=normalizeBrand({...BRAND_DEFAULTS,app_name:'Energi Berau'});
 assert.ok(cacheBrand(store,b));assert.equal(readCachedBrand(store).app_name,'Energi Berau');
 assert.equal(Object.keys(JSON.parse(mem.get(STORAGE_KEY))).includes('csrf'),false);
 assert.equal(cacheBrand({setItem:()=>{throw Error('no storage')}},b),false);
});
