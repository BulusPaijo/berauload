import test from 'node:test';
import assert from 'node:assert/strict';
import {EMPTY_LAYOUT,clone,addMetricBox,place,duplicateBox,removeBox,assetDraft,
 rebindBox,validEditorMetric,applySameKind} from '../src/features/topology/editorState.mjs';

const assets=[
 {id:1,code:'gen_a',name:'Generator A',kind:'PEMBANGKIT',active:true},
 {id:2,code:'gen_b',name:'Generator B',kind:'PEMBANGKIT',active:true},
 {id:3,code:'unknown',name:'Unknown',kind:'LAIN',active:true},
];
const metrics=[
 {id:1,code:'gen_a_kw',name:'Output Daya',unit:'kW',asset_id:1,active:true},
 {id:2,code:'gen_b_kw',name:'Output Daya',unit:'kW',asset_id:2,active:true},
 {id:3,code:'gen_b_hz',name:'Frekuensi',unit:'Hz',asset_id:2,active:false},
 {id:4,code:'daya_mampu_sistem_kw',name:'Legacy',unit:'kW',asset_id:null,active:true}
];

test('kotak baru tidak menambah jalur atau nilai pengukuran',()=>{
 const input=clone(EMPTY_LAYOUT);
 const out=addMetricBox(input,{asset_code:'gen_a',metric_code:'gen_a_kw',title:'Generator A'});
 assert.equal(input.boxes.length,0);
 assert.equal(out.boxes.length,1);
 assert.deepEqual(out.wires,[]);
 assert.deepEqual(out.boxes[0].metric_codes,['gen_a_kw']);
 assert.equal(Object.hasOwn(out.boxes[0],'value'),false);
 assert.equal(out.boxes[0].x%10,0);
});

test('pindah snap grid, clamp kanvas, dan patuhi locked',()=>{
 let layout=addMetricBox(EMPTY_LAYOUT,{asset_code:null,metric_code:'gen_a_kw'});
 const id=layout.boxes[0].id;
 layout=place(layout,id,'box',46,57);
 assert.equal(layout.boxes[0].x,50);assert.equal(layout.boxes[0].y,60);
 layout=place(layout,id,'box',99999,99999);
 assert.ok(layout.boxes[0].x+layout.boxes[0].w<=1600);
 assert.ok(layout.boxes[0].y+97<=900);
 layout.boxes[0].locked=true;
 const frozen=place(layout,id,'box',100,200);
 assert.equal(frozen.boxes[0].x,layout.boxes[0].x);
});

test('duplikat dan hapus hanya mengubah JSON layout',()=>{
 const src=addMetricBox(EMPTY_LAYOUT,{asset_code:'gen_a',metric_code:'gen_a_kw'});
 const duplicated=duplicateBox(src,src.boxes[0].id);
 assert.equal(duplicated.boxes.length,2);
 assert.notEqual(duplicated.boxes[0].id,duplicated.boxes[1].id);
 assert.equal(removeBox(duplicated,duplicated.boxes[0].id).boxes.length,1);
 assert.equal(src.boxes.length,1);
});

test('draf aset menempatkan simbol yang diketahui tanpa sambungan',()=>{
 const {layout,added,skipped}=assetDraft(EMPTY_LAYOUT,assets);
 assert.equal(added,2);assert.equal(skipped,1);
 assert.deepEqual(layout.wires,[]);
 assert.deepEqual(layout.boxes,[]);
 assert.ok(layout.symbols.every(s=>s.type==='generator'));
});

test('parameter legacy dan tidak aktif ditolak dari pemilih editor',()=>{
 assert.equal(validEditorMetric(metrics[0],'gen_a',assets),true);
 assert.equal(validEditorMetric(metrics[0],'gen_b',assets),false);
 assert.equal(validEditorMetric(metrics[2],null,assets),false);
 assert.equal(validEditorMetric(metrics[3],null,assets),false);
 const src=addMetricBox(EMPTY_LAYOUT,{asset_code:'gen_a',metric_code:'gen_a_kw'});
 const rebound=rebindBox(src,src.boxes[0].id,'gen_b',['gen_b_kw']);
 assert.deepEqual(rebound.boxes[0].metric_codes,[]);
});

test('terapkan peralatan sejenis hanya jika parameter nama dan unit cocok persis',()=>{
 const source=addMetricBox(EMPTY_LAYOUT,{asset_code:'gen_a',metric_code:'gen_a_kw'});
 const result=applySameKind(source,source.boxes[0].id,assets,metrics);
 assert.equal(result.added,1);assert.equal(result.skipped,0);
 assert.equal(result.layout.boxes[1].asset_code,'gen_b');
 assert.deepEqual(result.layout.boxes[1].metric_codes,['gen_b_kw']);
 assert.equal(result.layout.boxes[1].rule_id,null);
 assert.deepEqual(result.layout.wires,[]);
 assert.equal(source.boxes.length,1);
});
