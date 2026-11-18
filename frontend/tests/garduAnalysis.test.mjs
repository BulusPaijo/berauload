import test from 'node:test';
import assert from 'node:assert/strict';
import {fromQuery,toQuery,chips,valueText,direction,applyView,serializeView} from '../src/features/substations/analysis/helpers.mjs';
test('filter disimpan sebagai query URL dan pulih saat dibuka',()=>{
 const input={...fromQuery(''),category:'overload',findings:['a','b'],mode:'semua',page:'2'};
 const query=toQuery(input);assert.equal(fromQuery(query).category,'overload');
 assert.deepEqual(fromQuery(query).findings,['a','b']);assert.equal(fromQuery(query).page,'2');
});
test('chip dinamis bergantung pada definisi aktif, bukan kode tetap',()=>{
 assert.deepEqual(chips([{active:true,kind:'category',code:'baru',name:'Baru',color:'#123456',group_name:'X'},
  {active:false,kind:'finding',code:'arsip'}]).map(x=>x.code),['baru']);
});
test('format NULL dan nol tetap berbeda; penanda tidak lengkap',()=>{
 assert.equal(valueText(null),'—');assert.equal(valueText(0),'0');
 assert.match(valueText(12,1,true),/⚠/);
});
test('sortir dan tampilan tersimpan tetap konsisten',()=>{
 const f=fromQuery('sort=code&desc=false');assert.deepEqual(direction(f,'code'),{sort:'code',desc:'true'});
 const data=serializeView(f,['code','foo'],{foo:140});
 assert.deepEqual(applyView({layout:data}).findings,[]);
 assert.deepEqual(data.columns,['code','foo']);
});
import {recalcDecision,orderedCodes} from '../src/features/substations/formulas/helpers.mjs';
test('kategori diurutkan dari definisi dan menukar posisi saja',()=>{
 const rules=[{id:2,code:'b',display_order:20},{id:1,code:'a',display_order:10},
  {id:3,code:'c',display_order:30}];
 assert.deepEqual(orderedCodes(rules,'b',-1),['b','a','c']);
 assert.deepEqual(orderedCodes(rules,'b',1),['a','c','b']);
});
test('busy mengulang tanpa dianggap error atau berhenti',()=>{
 assert.equal(recalcDecision({busy:true,remaining:200,processed:0}),'retry');
 assert.equal(recalcDecision({busy:false,remaining:200,processed:100}),'continue');
 assert.equal(recalcDecision({busy:false,remaining:0,processed:0}),'stop');
});

test('tampilan dengan kolom atau aturan diarsipkan tetap bisa dibuka',()=>{
 const definitions={columns:[{code:'total_r',active:true}],fields:[],rules:[
  {code:'normal',kind:'category',active:true},{code:'aktif',kind:'finding',active:true}]};
 const saved={layout:{sort:'kolom_arsip',category:'kategori_arsip',numeric_code:'rumus_arsip',
  findings:['aktif','temuan_arsip'],columns:['code','total_r','kolom_arsip']}};
 const loaded=applyView(saved,definitions);
 assert.equal(loaded.sort,'code');assert.equal(loaded.category,'');assert.equal(loaded.numeric_code,'');
 assert.deepEqual(loaded.findings,['aktif']);assert.deepEqual(loaded.columns,['code','total_r']);
});

test('URL temuan mengirim parameter berulang dan membaca semuanya',()=>{
 const payload={...fromQuery(''),findings:['kandidat_mutasi','grounding']};
 const url=toQuery(payload);const params=new URLSearchParams(url);
 assert.deepEqual(params.getAll('findings'),['kandidat_mutasi','grounding']);
 assert.deepEqual(fromQuery('?'+url).findings,['kandidat_mutasi','grounding']);
});
