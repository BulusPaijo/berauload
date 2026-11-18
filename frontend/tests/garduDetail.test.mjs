import test from 'node:test';
import assert from 'node:assert/strict';
import {phaseBars,lineTable,trendRows,mapsLink,phaseTone} from '../src/features/substations/detail/detail.mjs';
test('arus per fasa terhadap In, nada warna dan netral netral',()=>{
 const b=phaseBars({arus_nominal:{value:200},total_r:{value:220},total_s:{value:170},total_t:{value:100},total_n:{value:40}});
 assert.deepEqual(b.map(x=>[x.letter,Math.round(x.pct),x.tone]),[['R',110,'over'],['S',85,'high'],['T',50,'ok'],['N',20,'neutral']]);
 assert.equal(phaseBars({total_r:{value:10}})[0].pct,null);assert.equal(phaseTone(null),'none');
});
test('tabel per jurusan: label pendek, penanda tetap teks, kosong null',()=>{
 const P=[{id:1,name:'Arus R',scope:'line',unit:'A',active:true,display_order:1},{id:2,name:'Arus S',scope:'line',unit:'A',active:true,display_order:2},
  {id:3,name:'Tegangan ujung R-N',scope:'line',unit:'V',active:true,display_order:3}];
 const t=lineTable(P,[{param_id:1,line_no:2,value:5,flag:null},{param_id:2,line_no:1,value:null,flag:'PUTUS'},{param_id:3,line_no:1,value:220,flag:null}]);
 assert.deepEqual(t.head,['R','S']);assert.deepEqual(t.rows,[{line:1,cells:[null,'PUTUS']},{line:2,cells:[5,null]}]);
});
test('riwayat per sesi dan tautan peta',()=>{
 const r=trendRows([{day:'2026-01-01',session:'SIANG',value:50},{day:'2026-01-01',session:'MALAM',value:70},{day:'2026-02-01',session:'MALAM',value:80}]);
 assert.deepEqual(r.sessions,['SIANG','MALAM']);assert.equal(r.rows.length,2);assert.equal(r.rows[1].SIANG,undefined);
 assert.equal(mapsLink(null,1),null);assert.equal(mapsLink(2.1,117.5),'https://www.google.com/maps?q=2.1,117.5');
});
