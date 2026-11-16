import test from 'node:test';
import assert from 'node:assert/strict';
import {pickUnit,canWrite,isRootOnly,cacheUnitKey,viewModeLabel,rootDataHint} from './unitSelection.mjs';
const tree=[{id:1,level:'up3',active:true,children:[{id:2,level:'ulp',active:true,legacy_home:true,roles:['management'],children:[]}]}];
test('invalid stored unit falls back to authorized active legacy home',()=>assert.equal(pickUnit(tree,77).id,2));
test('no writing for management and root selected',()=>{assert.equal(canWrite(tree[0].children[0],'management'),false);assert.equal(isRootOnly(tree[0]),true)});
test('cache keys isolate users and units',()=>assert.notEqual(cacheUnitKey(1,2,'catalog'),cacheUnitKey(1,3,'catalog')));
test('read-only and UP3 hints are stable',()=>{
 assert.equal(viewModeLabel(tree[0].children[0],'management'),'Hanya lihat');
 assert.equal(rootDataHint(tree[0]),'Pilih ULP atau KP');
 assert.equal(rootDataHint(tree[0].children[0]),null);
});
