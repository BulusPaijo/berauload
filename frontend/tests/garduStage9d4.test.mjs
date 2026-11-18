import test from 'node:test';
import assert from 'node:assert/strict';
import {editableBody,formFromRow} from '../src/features/substations/masterForm.mjs';
import {headerPlan,orderColumns,columnsFromParams,mobileSections} from '../src/features/substations/grid.mjs';
const blank={unit_id:'',code:'',name:'',feeder_id:'',power_kva:'',phase:'3',line_count:'1',ownership:'PLN',purpose:'UMUM',address:'',brand:'',tap:'',serial_number:'',year:'',lat:'',lon:'',line_labels:'',extra_values:'{}'};
test('ubah gardu: hanya field yang diterima API (regresi 422 id/unit_id/created_at)',()=>{
 const row={id:1,unit_id:3,code:'A',name:'Gardu A',feeder_id:1,power_kva:200,phase:3,line_count:1,ownership:'PLN',purpose:'UMUM',address:null,
  brand:null,tap:null,serial_number:null,year:null,lat:2.17,lon:117.6,line_labels:['Barat'],extra_values:{x:'1'},active:true,created_by:1,updated_by:1,created_at:'2026-11-17',updated_at:'2026-11-17'};
 const form=formFromRow(blank,row);form.name='Nama baru';
 const body=editableBody(form,false,false);
 for(const k of ['id','unit_id','created_by','updated_by','created_at','updated_at','active','code'])assert.equal(k in body,false,k);
 assert.equal(body.name,'Nama baru');assert.equal(body.lat,2.17);assert.equal(body.year,null);assert.deepEqual(body.line_labels,['Barat']);
 assert.deepEqual(body.extra_values,{x:'1'});
 const moved=editableBody({...form,unit_id:'7'},false,true);assert.equal(moved.unit_id,7);
 const created=editableBody({...blank,code:' G1 ',name:'G',power_kva:'50',lat:'2,5'},true,false);assert.equal(created.code,'G1');assert.equal(created.lat,2.5);
 assert.throws(()=>editableBody({...form,extra_values:'{bad'},false,false),/Atribut/);
});
test('tegangan ujung per gardu terpisah dari tegangan rel (blok sendiri)',()=>{
 const P=[['I_R','Arus R','line','V',1],['V_R0','Tegangan Rel R-N','substation','V',5],['V_S0','Tegangan Rel S-N','substation','V',6],
  ['V_END_RN','Tegangan Ujung JTR R-N','substation','V',10],['V_END_SN','Tegangan Ujung JTR S-N','substation','V',11]]
  .map(([code,name,scope,unit,display_order])=>({code,name,scope,unit,display_order,active:true}));
 const plan=headerPlan(orderColumns(columnsFromParams(P,null),2));
 assert.deepEqual(plan.map(b=>[b.title,b.span]),[['Jurusan 1',1],['Jurusan 2',1],['Tegangan Rel F-N',2],['Tegangan Ujung JTR',2]]);
 assert.deepEqual(plan[3].cells.map(c=>[c.sub,c.phase]),[['R-N','R'],['S-N','S']]);
 assert.deepEqual(mobileSections(P,2).map(s=>s.title),['Jurusan 1','Jurusan 2','Tegangan Rel F-N','Tegangan Ujung JTR']);
});
test('grounding trafo + arester tetap satu kartu/blok',()=>{
 const P=[['GROUND_TR','Grounding Trafo','substation','ohm',9],['GROUND_AR','Grounding Arrester','substation','ohm',10]]
  .map(([code,name,scope,unit,display_order])=>({code,name,scope,unit,display_order,active:true}));
 const plan=headerPlan(orderColumns(columnsFromParams(P,null),1));
 assert.deepEqual(plan.map(b=>[b.title,b.unit,b.span]),[['Grounding','Ω',2]]);
 assert.deepEqual(plan[0].cells.map(c=>c.sub),['Trafo','Arrester']);
 assert.deepEqual(mobileSections(P,1).map(s=>[s.title,s.rows.length]),[['Grounding',2]]);
});
