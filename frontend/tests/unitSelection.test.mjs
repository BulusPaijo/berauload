import test from 'node:test';
import assert from 'node:assert/strict';
import {pickUnit,cacheUnitKey,viewModeLabel,rootDataHint} from '../src/features/org-units/unitSelection.mjs';
import {setActiveUnit,unitCacheKey} from '../src/api.ts';

const up3 = {
  id: 1, code: 'UP3', level: 'up3', active: true, roles: ['management'],
  children: [{
    id: 2, code: 'ULP_TR', level: 'ulp', active: true, legacy_home: true,
    roles: ['management'], children: [
      {id: 3, code: 'KP_1', level: 'kp', active: false, roles: ['operator'], children: []},
    ],
  }],
};

test('unit tersimpan tidak valid atau nonaktif jatuh ke unit bawaan aktif', () => {
  assert.equal(pickUnit([up3], 999)?.id, 2);
  assert.equal(pickUnit([up3], 3)?.id, 2);
  assert.equal(pickUnit([up3], 2)?.id, 2);
});

test('kunci cache mengisolasi unit dan pengguna', () => {
  assert.notEqual(cacheUnitKey(10, 2, 'catalog'), cacheUnitKey(10, 3, 'catalog'));
  assert.notEqual(cacheUnitKey(10, 2, 'catalog'), cacheUnitKey(11, 2, 'catalog'));
  setActiveUnit(2);
  const first = unitCacheKey('berauload_day');
  setActiveUnit(3);
  const second = unitCacheKey('berauload_day');
  setActiveUnit(null);
  assert.notEqual(first, second);
});

test('unit tanpa hak tulis menampilkan Hanya lihat', () => {
  assert.equal(viewModeLabel(up3.children[0], 'management'), 'Hanya lihat');
  assert.equal(viewModeLabel(up3.children[0], 'admin'), null);
});

test('UP3 menampilkan Pilih ULP atau KP', () => {
  assert.equal(rootDataHint(up3), 'Pilih ULP atau KP');
  assert.equal(rootDataHint(up3.children[0]), null);
});
