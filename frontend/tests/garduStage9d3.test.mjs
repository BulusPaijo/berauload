import test from 'node:test';
import assert from 'node:assert/strict';
import {rowState,codesForGroups,summarizeRows,mobileSections,filledCount} from '../src/features/substations/grid.mjs';
const P=[['I_R','Arus R','line','A',1],['I_S','Arus S','line','A',2],['I_T','Arus T','line','A',3],['I_N','Arus Netral','line','A',4],
 ['V_R0','Tegangan Rel R-0','substation','V',5],['V_S0','Tegangan Rel S-0','substation','V',6],['GROUND_TR','Grounding Trafo','substation','ohm',9],
 ['V_END_RN','Tegangan Ujung JTR R-N','line','V',10],['V_END_SN','Tegangan Ujung JTR S-N','line','V',11]]
 .map(([code,name,scope,unit,display_order])=>({code,name,scope,unit,display_order,active:true}));
test('status baris: konflik > terkunci > antrean > isi',()=>{
 assert.equal(rowState({verified:true,conflict:true,filled:true}).tone,'danger');
 assert.equal(rowState({verified:true,conflict:false,filled:true}).label,'Terkunci (verified)');
 assert.equal(rowState({verified:false,conflict:false,queue:'menyimpan',filled:true}).tone,'warn');
 assert.equal(rowState({verified:false,conflict:false,queue:'tersimpan 10.42.11',filled:true}).label,'Tersimpan 10.42');
 assert.equal(rowState({verified:false,conflict:false,filled:false}).label,'Belum diisi');
 const sum=summarizeRows([rowState({filled:true}),rowState({filled:false}),rowState({conflict:true})]);
 assert.deepEqual(sum,{saved:1,saving:0,conflict:1,empty:1});
});
test('chip kolom multi-pilih; kosong = semua',()=>{
 const g=[{name:'A',codes:['I_R']},{name:'B',codes:['V_R0']}];
 assert.equal(codesForGroups(g,[]),null);assert.deepEqual(codesForGroups(g,['B']),['V_R0']);
});
test('form ponsel: kartu per jurusan dipisah satuan, baris berlabel fasa',()=>{
 const s=mobileSections(P,2);
 assert.deepEqual(s.map(x=>x.title),['Jurusan 1','Jurusan 1','Jurusan 2','Jurusan 2','Tegangan Rel F-N','Grounding Trafo']);
 const arus=s.find(x=>x.line===1&&x.unit==='A');
 assert.deepEqual(arus.rows.map(r=>[r.label,r.phase]),[['R','R'],['S','S'],['T','T'],['Netral','N']]);
 const ujung=s.find(x=>x.line===1&&x.unit==='V');
 assert.equal(ujung.topic,'Tegangan Ujung JTR');assert.deepEqual(ujung.rows.map(r=>r.phase),['R','S']);
 assert.equal(s.filter(x=>x.line===3).length,0);
 const key=(c,l)=>`${c}:${l}`;assert.equal(filledCount(arus.rows,{'I_R:1':'5','I_S:1':'','I_T:1':'@PUTUS'},key),2);
});
