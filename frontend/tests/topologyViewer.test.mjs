import test from 'node:test';
import assert from 'node:assert/strict';
import {formatMetric,hourLabel,dayStatus,trendPoints} from '../src/features/topology/viewerFormatting.mjs';

test('NULL and unavailable are em dash, but measured zero is 0',()=>{
 assert.equal(formatMetric(null),'—');
 assert.equal(formatMetric(undefined),'—');
 assert.equal(formatMetric(0),'0');
 assert.equal(formatMetric(1250.234,2),'1.250,23');
});
test('hour and day status use the approved historical labels',()=>{
 assert.equal(hourLabel(0),'00:00');
 assert.equal(hourLabel(23),'23:00');
 assert.equal(dayStatus('draft'),'Draft / belum difinalkan');
 assert.equal(dayStatus('verified'),'Terverifikasi');
 assert.equal(dayStatus('final'),'Final');
});
test('trend preserves 24 slots, zero, missing hours and out-of-order API points',()=>{
 const points=trendPoints({series:{beban:[{hour:15,value:43},{hour:0,value:0},{hour:8,value:null}]}},'beban');
 assert.equal(points.length,24);
 assert.deepEqual(points[0],{jam:'00:00',nilai:0});
 assert.deepEqual(points[8],{jam:'08:00',nilai:null});
 assert.deepEqual(points[15],{jam:'15:00',nilai:43});
 assert.equal(points[12].nilai,null);
 assert.equal(trendPoints(null,'beban').length,24);
});
