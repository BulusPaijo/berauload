import test from 'node:test';
import assert from 'node:assert/strict';
import {addColumn,buildSpec,filterBody,fromTemplate,groupCatalog,moveColumn,removeColumn,renameColumn,sizeNote,validateSpec,MAX_COLUMNS} from '../src/features/substations/export/spec.mjs';

test('filterBody converts Analisa query state to API body', () => {
  const body = filterBody({mode:'periode',start:'2026-01-01',end:'2026-01-31',unit_id:'7',min_kva:'50',desc:'true',findings:['a','b'],page:'3',page_size:'50',text:'',category:'overload'});
  assert.deepEqual(body,{mode:'periode',start:'2026-01-01',end:'2026-01-31',unit_id:7,min_kva:50,desc:true,findings:['a','b'],category:'overload'});
  assert.equal('page' in body,false);
  assert.equal(filterBody({min_kva:'abc'}).min_kva,undefined);
});
test('column list operations keep order, uniqueness and limit', () => {
  let cols = addColumn([], 'code'); cols = addColumn(cols,'name'); cols = addColumn(cols,'code');
  assert.deepEqual(cols.map(c=>c.key),['code','name']);
  cols = moveColumn(cols,1,-1); assert.deepEqual(cols.map(c=>c.key),['name','code']);
  assert.equal(moveColumn(cols,0,-1),cols);
  cols = renameColumn(cols,'code','Kode');
  assert.deepEqual(buildSpec({columns:cols,shape:'wide',format:'csv',delimiter:';'}).columns,[{key:'name'},{key:'code',header:'Kode'}]);
  assert.deepEqual(removeColumn(cols,'name').map(c=>c.key),['code']);
  let big = []; for (let i=0;i<MAX_COLUMNS+5;i++) big = addColumn(big,'k'+i);
  assert.equal(big.length,MAX_COLUMNS);
});
test('groupCatalog hides chosen, filters search, drops wide params for long shape', () => {
  const items=[{key:'code',label:'Kode gardu',group:'Identitas'},{key:'param:I_R:1',label:'Arus R J1',group:'Nilai ukur'},{key:'calc:x',label:'Beban',group:'Hasil hitung'}];
  assert.deepEqual(groupCatalog(items,['code'],'','wide').map(g=>g.group),['Nilai ukur','Hasil hitung']);
  assert.deepEqual(groupCatalog(items,[],'beban','wide').map(g=>g.entries[0].key),['calc:x']);
  assert.deepEqual(groupCatalog(items,[],'','long').map(g=>g.group),['Identitas','Hasil hitung']);
});
test('validateSpec reports empty, long+param, missing and long header', () => {
  const keys=new Set(['code']);
  assert.deepEqual(validateSpec({columns:[],shape:'wide'},keys),['Pilih minimal satu kolom']);
  assert.ok(validateSpec({columns:[{key:'param:I_R:1'}],shape:'long'},keys).length>=1);
  assert.match(validateSpec({columns:[{key:'zzz'}],shape:'wide'},keys).join(),/zzz/);
  assert.deepEqual(validateSpec({columns:[{key:'code',header:'x'.repeat(81)}],shape:'wide'},keys),['Judul kolom maksimal 80 karakter']);
  assert.deepEqual(validateSpec({columns:[{key:'code'}],shape:'wide'},keys),[]);
});
test('fromTemplate drops archived columns but reports them; normalizes options', () => {
  const r=fromTemplate({spec:{columns:[{key:'code',header:'K'},{key:'calc:gone'}],shape:'long',format:'csv',delimiter:','}},new Set(['code']));
  assert.deepEqual(r.columns,[{key:'code',header:'K'}]); assert.deepEqual(r.dropped,['calc:gone']);
  assert.equal(r.shape,'long'); assert.equal(r.delimiter,','); 
  assert.equal(fromTemplate({spec:{columns:[],shape:'zzz',format:'pdf'}}).shape,'wide');
});
test('sizeNote levels', () => {
  assert.equal(sizeNote(10,100).level,'ok'); assert.equal(sizeNote(70,100).level,'warn'); assert.equal(sizeNote(101,100).level,'error');
});
