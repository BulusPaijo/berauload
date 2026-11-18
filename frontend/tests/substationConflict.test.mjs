import test from 'node:test';
import assert from 'node:assert/strict';
import {conflictCells} from '../src/features/substations/conflict.mjs';
const params=[{id:1,code:'I_R',name:'Arus R'},{id:2,code:'GROUND_TR',name:'Grounding Trafo'}];
test('perbandingan konflik menampilkan hanya sel yang berbeda, termasuk nol, kosong, dan flag',()=>{
 const drafts={'4|I_R|1':'0','4|I_R|2':'','4|GROUND_TR|0':'@PUTUS','5|I_R|1':'99'};
 const server=[{param_id:1,line_no:1,value:0,flag:null},
  {param_id:1,line_no:2,value:7,flag:null},
  {param_id:2,line_no:0,value:null,flag:'TIDAK_TERUKUR'}];
 const changes=conflictCells(drafts,4,server,params);
 assert.equal(changes.length,2);
 assert.deepEqual(changes.map(c=>c.label),['Arus R','Grounding Trafo']);
 assert.equal(changes[0].mine,'');assert.equal(changes[0].server,'7');
 assert.equal(changes[1].mine,'@PUTUS');
});
