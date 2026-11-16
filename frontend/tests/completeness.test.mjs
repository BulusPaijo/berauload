import test from 'node:test';
import assert from 'node:assert/strict';
import {basisLabel,statusLetter,cellLabel,coverageLabel,initialRange} from '../src/features/completeness/completeness.mjs';
test('zero is filled and status letters remain visible',()=>{
 assert.equal(cellLabel({filled_hours:0,expected_hours:24,status:'draft',future:false}),'0/24 D');
 assert.equal(statusLetter('verified'),'V');assert.equal(statusLetter('final'),'F');
 assert.match(cellLabel({filled_hours:0,expected_hours:0,status:'draft',future:true}),/masa depan/);
});
test('basis and coverage percent are explicit',()=>{
 assert.equal(basisLabel('system.load'),'dasar: beban sistem');
 assert.equal(basisLabel('any_input'),'dasar: parameter input apa pun');
 assert.equal(coverageLabel({percent:null}),'—');
 assert.equal(coverageLabel({percent:50}),'50%');
});
test('default dates are 14 days inclusive',()=>{
 assert.deepEqual(initialRange('2026-11-16'),['2026-11-03','2026-11-16']);
});
