import test from 'node:test';
import assert from 'node:assert/strict';
import {columnsFromParams,orderColumns,headerPlan,shortLabels,allowedCell} from '../src/features/substations/grid.mjs';
const P=[['I_R','Arus R','line','A',1],['I_S','Arus S','line','A',2],['I_T','Arus T','line','A',3],['I_N','Arus N','line','A',4],
 ['V_R0','Tegangan rel R-N','substation','V',5],['V_END_RN','Tegangan ujung R-N','line','V',8],['GROUND_TR','Grounding trafo','substation','Ω',9]]
 .map(([code,name,scope,unit,display_order])=>({code,name,scope,unit,display_order,active:true}));
test('arus: blok Jurusan n bergabung di atas R S T N, satuan sekali',()=>{
 for(const max of [1,3,5]){
  const plan=headerPlan(orderColumns(columnsFromParams(P,['I_R','I_S','I_T','I_N']),max));
  assert.equal(plan.length,max);
  assert.deepEqual(plan.map(b=>b.title),Array.from({length:max},(_,i)=>`Jurusan ${i+1}`));
  assert.ok(plan.every(b=>b.span===4&&b.unit==='A'));
  assert.deepEqual(plan[0].cells.map(c=>c.sub),['R','S','T','N']);
  assert.deepEqual(plan[0].cells.map(c=>c.phase),['R','S','T','N']);
 }
});
test('urutan: jurusan dulu, blok per satuan, parameter gardu di akhir',()=>{
 const cols=orderColumns(columnsFromParams(P,null),2);
 assert.deepEqual(cols.slice(-2).map(c=>c.code),['V_R0','GROUND_TR']);
 assert.deepEqual(cols.filter(c=>c.line===1).map(c=>c.code),['I_R','I_S','I_T','I_N','V_END_RN']);
 const plan=headerPlan(cols);
 assert.deepEqual(plan.map(b=>[b.title,b.unit,b.span]),[['Jurusan 1','A',4],['Jurusan 1 · Tegangan ujung R-N','V',1],
  ['Jurusan 2','A',4],['Jurusan 2 · Tegangan ujung R-N','V',1],['Tegangan Rel F-N','V',1],['Grounding trafo','Ω',1]]);
});
test('parameter baru buatan admin muncul otomatis di blok jurusan',()=>{
 const extra=[...P,{code:'I_X',name:'Arus X',scope:'line',unit:'A',display_order:4.5,active:true}];
 const plan=headerPlan(orderColumns(columnsFromParams(extra,['I_R','I_S','I_T','I_N','I_X']),1));
 assert.deepEqual(plan[0].cells.map(c=>c.sub),['R','S','T','N','X']);
});
test('tegangan ujung: R-N S-N T-N; sel jurusan di luar gardu tidak boleh diisi',()=>{
 const p=[...P,{code:'V_END_SN',name:'Tegangan ujung S-N',scope:'line',unit:'V',display_order:8.1,active:true}];
 const plan=headerPlan(orderColumns(columnsFromParams(p,['V_END_RN','V_END_SN']),2));
 assert.deepEqual(plan[1].cells.map(c=>[c.sub,c.phase]),[['R-N','R'],['S-N','S']]);
 assert.equal(allowedCell({id:1,line_count:1},{code:'V_END_RN',line:2}),false);
 assert.deepEqual(shortLabels(['Arus R']),['Arus R']);
});
