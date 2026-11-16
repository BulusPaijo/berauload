import test from 'node:test';
import assert from 'node:assert/strict';
import {EMPTY_LAYOUT,addMetricBox,applySameKind} from '../src/features/topology/editorState.mjs';

const assets = [
 {id:101,code:'unit_a',name:'Unit A',kind:'generator',unit_id:4,active:true},
 {id:102,code:'unit_b',name:'Unit B',kind:'generator',unit_id:4,active:true},
 {id:103,code:'unit_other',name:'Unit Other',kind:'generator',unit_id:9,active:true},
];

test('terapkan kotak mendahulukan role_key saat nama parameter berbeda',()=>{
 const metrics = [
  {id:1,code:'a_output',asset_id:101,name:'Beban Utama',unit:'kW',role_key:'generator.output',active:true},
  {id:2,code:'b_output',asset_id:102,name:'Output Generator',unit:'kW',role_key:'generator.output',active:true},
  {id:3,code:'other_output',asset_id:103,name:'Output Generator',unit:'kW',role_key:'generator.output',active:true},
 ];
 const layout=addMetricBox(EMPTY_LAYOUT,{asset_code:'unit_a',metric_code:'a_output'});
 const out=applySameKind(layout,layout.boxes[0].id,assets,metrics);
 assert.equal(out.added,1);
 assert.equal(out.layout.boxes[1].asset_code,'unit_b');
 assert.deepEqual(out.layout.boxes[1].metric_codes,['b_output']);
 assert.ok(out.layout.boxes.every(b=>b.asset_code!=='unit_other'));
});

test('role_key kosong mempertahankan matching nama dan satuan yang presisi',()=>{
 const metrics = [
  {id:1,code:'a_output',asset_id:101,name:'Output',unit:'kW',role_key:null,active:true},
  {id:2,code:'b_output',asset_id:102,name:'Output',unit:'MW',role_key:null,active:true},
 ];
 const layout=addMetricBox(EMPTY_LAYOUT,{asset_code:'unit_a',metric_code:'a_output'});
 const out=applySameKind(layout,layout.boxes[0].id,assets,metrics);
 assert.equal(out.added,0);
 assert.equal(out.skipped,1);
 assert.equal(out.layout.boxes.length,1);
});
