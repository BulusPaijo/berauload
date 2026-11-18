import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {originLabel,insertToken,displayValue,errorMessage} from '../src/features/substations/formulas/helpers.mjs';

test('label Bawaan, Diubah, Kustom akurat',()=>{
  assert.equal(originLabel({origin:'default',expression:'kva',default_expression:'kva'}),'Bawaan');
  assert.equal(originLabel({origin:'default',expression:'kva*2',default_expression:'kva'}),'Diubah');
  assert.equal(originLabel({origin:'custom',expression:'kva*2'}),'Kustom');
});
test('sisip teks fungsi pada posisi kursor editor',()=>{
 const result=insertToken('SUM()','i_r',4,4);
 assert.deepEqual(result,{value:'SUM(i_r)',caret:7});
});
test('nilai nol tetap 0, NULL berupa tanda — dan tidak lengkap terbaca',()=>{
 assert.equal(displayValue(0,1),'0');
 assert.equal(displayValue(null),'—');
 assert.match(displayValue(5,2,true),/Tidak lengkap/);
});
test('galat server dan galat lain dipetakan sebagai teks',()=>{
 assert.equal(errorMessage(new Error('Kode tidak dikenal')),'Kode tidak dikenal');
 assert.equal(errorMessage('Gagal'), 'Gagal');
});
