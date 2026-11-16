export function flattenUnits(tree){return tree.flatMap(unit=>[unit,...flattenUnits(unit.children||[])]);}
export function pickUnit(tree,saved){const all=flattenUnits(tree).filter(u=>u.active);
 return all.find(u=>u.id===saved)||all.find(u=>u.legacy_home)||all.find(u=>u.level!=='up3')||all[0]||null;}
export function canWrite(unit,globalRole){return !!unit&&unit.level!=='up3'&&(
 globalRole==='admin'||(unit.roles||[]).some(r=>r==='operator'||r==='verifier'));}
export function isRootOnly(unit){return !unit||unit.level==='up3';}
export function cacheUnitKey(userId,unitId,key){return `${userId}:${unitId}:${key}`;}
export function viewModeLabel(unit,role){return canWrite(unit,role)?null:'Hanya lihat';}
export function rootDataHint(unit){return isRootOnly(unit)?'Pilih ULP atau KP':null;}
