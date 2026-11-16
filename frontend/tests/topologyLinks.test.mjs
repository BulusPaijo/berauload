import test from 'node:test';
import assert from 'node:assert/strict';
import {patchSymbol} from '../src/features/topology/stage4State.mjs';
const source={canvas:{w:1600,h:900,grid:10},symbols:[{id:'sym1',type:'feeder',x:10,y:10,w:120,h:70,asset_code:null,label:'Feeder',rotation:0}],wires:[],boxes:[]};
test('link metadata is editable and reversible without touching physical wires',()=>{
 const linked=patchSymbol(source,'sym1',{link:{unit_id:2,diagram_id:7}});
 assert.deepEqual(linked.symbols[0].link,{unit_id:2,diagram_id:7});
 assert.deepEqual(linked.wires,[]);
 assert.equal(source.symbols[0].link,undefined);
 const cleared=patchSymbol(linked,'sym1',{link:undefined});
 assert.equal('link' in cleared.symbols[0],false);
});
