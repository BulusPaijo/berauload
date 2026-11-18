import test from 'node:test';
import assert from 'node:assert/strict';
import {parseNumber,visitBackupKey,parsePaste,nextCell,fillDown,allowedCell,columnsFromParams} from '../src/features/substations/grid.mjs';

test('desimal koma, kosong NULL dan nol tetap nol',()=>{
 assert.equal(parseNumber('12,5'),12.5);assert.equal(parseNumber(''),null);
 assert.equal(parseNumber('0'),0);assert.throws(()=>parseNumber('bukan angka'));
});
test('paste berlapis mengabaikan luar kisi/jurusan tidak ada',()=>{
 const rows=[{id:1,line_count:1},{id:2,line_count:2}],cols=[{code:'I_R',line:1},{code:'I_R',line:2}];
 const p=parsePaste('1\t2\n3\t4\n5',0,0,rows,cols,allowedCell);
 assert.equal(p.changes['1|I_R|1'],'1');assert.equal(p.changes['1|I_R|2'],undefined);
 assert.equal(p.changes['2|I_R|2'],'4');assert.equal(p.omitted,2);
});
test('navigasi, isi bawah dan undo snapshot dapat dipulihkan',()=>{
 assert.deepEqual(nextCell(0,0,'Enter',3,5),[1,0]);
 const rows=[{id:1,line_count:1},{id:2,line_count:1}];
 const changes=fillDown(rows,{code:'I_R',line:1},0,1,()=> '0',allowedCell);
 assert.equal(changes['2|I_R|1'],'0');
 const before={};const after={...before,...changes};assert.deepEqual({...after,...before},{'2|I_R|1':'0'});
});
test('backup user/unit/day/session terpisah; kolom mengikuti admin',()=>{
 assert.notEqual(visitBackupKey(1,2,'2026-11-17','SIANG'),visitBackupKey(1,2,'2026-11-17','MALAM'));
 const cols=columnsFromParams([{code:'I_R',name:'Arus R',scope:'line',unit:'A',active:true,display_order:3},
 {code:'V_R0',name:'Rel R',scope:'substation',unit:'V',active:true,display_order:1}]);
 assert.equal(cols[0].code,'V_R0');assert.equal(cols.length,6);
});

test('queue per gardu tidak mengirim paralel dan cadangan terpisah',async()=>{
 const {HourQueue,saveBackup,readBackup}=await import('../src/features/input-form/autosave/core.mjs');
 const calls=[],statuses=[];let finish;
 const send=id=>{calls.push(id);return new Promise(resolve=>{finish=resolve})};
 const queue=new HourQueue(send,(id,status)=>statuses.push([id,status]),3000);
 queue.mark(123);
 const first=queue.flush(123);
 queue.mark(123);
 assert.equal(calls.length,1);
 finish();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(calls.length,2);
 finish();await first;
 assert.equal(calls.length,2);
 queue.stop();
 const map=new Map();const storage={setItem:(k,v)=>map.set(k,v),getItem:k=>map.get(k),removeItem:k=>map.delete(k)};
 const k=visitBackupKey(1,2,'2026-11-17','SIANG');
 saveBackup(storage,k,{'123|I_R|1':'0'},{});
 assert.equal(readBackup(storage,k).drafts['123|I_R|1'],'0');
 assert.equal(readBackup(storage,visitBackupKey(2,2,'2026-11-17','SIANG')),null);
});
