import test from 'node:test';
import assert from 'node:assert/strict';
import {EMPTY_LAYOUT,clone} from '../src/features/topology/editorState.mjs';
import {addSymbol,removeSymbol,patchSymbol,addWire,moveWirePoint,
 addWireVertex,removeWireVertex,removeWire,addDisplayBox,changeWireLevel}
 from '../src/features/topology/stage4State.mjs';
import {rankRows,availableCount,sparkSegments} from '../src/features/topology/boxView.mjs';

test('palet delapan simbol tidak pernah menambah sambungan listrik',()=>{
 for(const kind of ['generator','incoming','busbar','breaker','transformer','feeder','load','capacitor']){
  const source=clone(EMPTY_LAYOUT),result=addSymbol(source,kind,53,59);
  assert.equal(result.symbols.length,1);
  assert.equal(result.symbols[0].type,kind);
  assert.deepEqual(result.wires,[]);
  assert.equal(source.symbols.length,0);
  assert.equal(result.symbols[0].x%10,0);
 }
});
test('simbol dapat dirotasi, digeser dan hapus anchor tanpa menghapus jalur',()=>{
 let src=addSymbol(EMPTY_LAYOUT,'breaker',50,50);
 const id=src.symbols[0].id;
 src=patchSymbol(src,id,{rotation:90,x:1900});
 assert.equal(src.symbols[0].rotation,90);
 assert.ok(src.symbols[0].x+src.symbols[0].w<=1600);
 src=addDisplayBox(src,'legend');src.boxes[0].anchor_symbol_id=id;
 src.boxes[0].leader=true;src=addWire(src,[[0,0],[10,10]]);
 const output=removeSymbol(src,id);
 assert.equal(output.symbols.length,0);
 assert.equal(output.boxes[0].anchor_symbol_id,null);
 assert.equal(output.boxes[0].leader,false);
 assert.equal(output.wires.length,1);
});
test('garis manual memerlukan titik berbeda dan level whitelisted',()=>{
 assert.equal(addWire(EMPTY_LAYOUT,[[20,20],[20,20]]),null);
 assert.equal(addWire(EMPTY_LAYOUT,[[20,20],[30,30]],'#FF0000'),null);
 const source=addWire(EMPTY_LAYOUT,[[13,18],[31,38]],'unspecified');
 assert.deepEqual(source.wires[0].points,[[10,20],[30,40]]);
 assert.deepEqual(EMPTY_LAYOUT.wires,[]);
});
test('edit vertex mempertahankan 2-32 titik dan grid',()=>{
 let l=addWire(EMPTY_LAYOUT,[[10,10],[110,10]]),id=l.wires[0].id;
 l=addWireVertex(l,id,0);
 assert.deepEqual(l.wires[0].points,[[10,10],[60,10],[110,10]]);
 l=moveWirePoint(l,id,1,67,45);
 assert.deepEqual(l.wires[0].points[1],[70,50]);
 l=removeWireVertex(l,id,1);assert.equal(l.wires[0].points.length,2);
 l=removeWireVertex(l,id,0);assert.equal(l.wires[0].points.length,2);
 l=changeWireLevel(l,id,'20kv');assert.equal(l.wires[0].level,'20kv');
 l=removeWire(l,id);assert.deepEqual(l.wires,[]);
});
test('jenis kotak tidak menyimpan angka pengukuran dan nilai tidak dibuat-buat',()=>{
 let current=clone(EMPTY_LAYOUT);
 for(const kind of ['summary','ranking','legend','text']){
  current=addDisplayBox(current,kind,['summary','ranking'].includes(kind)?'beban_sistem_kw':null);
  assert.equal(current.boxes.at(-1).kind,kind);
  assert.equal(Object.hasOwn(current.boxes.at(-1),'value'),false);
 }
 assert.deepEqual(current.wires,[]);
 assert.equal(addDisplayBox(EMPTY_LAYOUT,'ranking'),null);
});
test('peringkat hanya nilai valid dalam satuan identik, nol tetap masuk',()=>{
 const ranked=rankRows(['a','b','c'],{a:0,b:null,c:5},{a:'kW',b:'kW',c:'kW'});
 assert.deepEqual(ranked.rows,[{code:'c',value:5},{code:'a',value:0}]);
 assert.equal(ranked.mixed,false);
 assert.equal(availableCount(['a','b','c'],{a:0,b:null,c:5}),2);
});
test('peringkat tidak membandingkan satuan berbeda',()=>{
 const ranked=rankRows(['a','b'],{a:100,b:3},{a:'kW',b:'Hz'});
 assert.equal(ranked.mixed,true);assert.deepEqual(ranked.rows,[]);
});
test('grafik mini tidak menyambung NULL, 0 adalah titik sah',()=>{
 const input=Array.from({length:24},(_,hour)=>({hour,value:null}));
 input[0].value=0;input[1].value=2;input[3].value=4;input[12].value=2;
 const seg=sparkSegments(input);
 assert.equal(seg.length,3);
 assert.equal(seg[0].length,2);
 assert.equal(seg[1].length,1);
 assert.equal(seg[2].length,1);
 assert.deepEqual(sparkSegments(input.map(x=>({...x,value:null}))),[]);
});
