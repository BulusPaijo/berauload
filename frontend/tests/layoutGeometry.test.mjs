import test from 'node:test';
import assert from 'node:assert/strict';
import {clamp,snapSize} from '../src/features/dashboard-builder/layoutGeometry.ts';

test('resize snaps to grid in both dimensions',()=>{
  assert.deepEqual(snapSize(4,1,220,275,50,260),{w:8,h:2});
  assert.deepEqual(snapSize(12,4,1000,1000,50,260),{w:12,h:4});
  assert.deepEqual(snapSize(4,1,-1000,-1000,50,260),{w:3,h:1});
  assert.deepEqual(snapSize(4,2,0,0,50,260),{w:4,h:2});
});

test('invalid layout measurements keep previous snapped size',()=>{
  assert.deepEqual(snapSize(6,2,99,99,0,0),{w:6,h:2});
  assert.equal(clamp(99,3,12),12);
});
