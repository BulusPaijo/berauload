import test from 'node:test';
import assert from 'node:assert/strict';
import {initialGrant,validateAccess,summarizeUserAccess} from '../src/features/users/userAccess.mjs';

test('peran pada unit biasa mengikuti pilihan; UP3 hanya management',()=>{
  assert.deepEqual(initialGrant({id:4,level:'ulp'},'verifier'),{unit_id:4,role:'verifier'});
  assert.deepEqual(initialGrant({id:1,level:'up3'},'operator'),{unit_id:1,role:'management'});
});

test('pengguna non-admin tanpa unit ditolak sebelum pengiriman',()=>{
  assert.match(validateAccess('operator',[]),/Pilih minimal satu unit/);
  assert.equal(validateAccess('management',[{unit_id:4,role:'management'}]),'');
  assert.equal(validateAccess('admin',[]),'');
});

test('akses unit ditampilkan dengan nama dan peran setiap pengguna',()=>{
  const rows=[{user_id:7,unit_id:4,role:'operator'},
    {user_id:7,unit_id:5,role:'verifier'},
    {user_id:8,unit_id:5,role:'management'}];
  const names=new Map([[4,'ULP Tanjung Redeb'],[5,'KP Sambaliung']]);
  assert.equal(summarizeUserAccess({id:7,role:'operator'},rows,names),
    'ULP Tanjung Redeb: operator · KP Sambaliung: verifier');
  assert.equal(summarizeUserAccess({id:8,role:'management'},rows,names),
    'KP Sambaliung: management');
  assert.equal(summarizeUserAccess({id:9,role:'management'},rows,names),
    'Belum ada akses unit');
});

test('admin ditampilkan sebagai akses global tanpa mengandalkan grant lama',()=>{
  assert.equal(summarizeUserAccess({id:1,role:'admin'},[],new Map()),
    'Semua unit (admin global)');
});
