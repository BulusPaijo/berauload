import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {EMPTY_LAYOUT,addMetricBox,place} from '../src/features/topology/editorState.mjs';
import {addArea,patchArea,removeArea,resizeCanvas,expandForRect,contentBounds} from '../src/features/topology/workspaceState.mjs';
import {comparisonAllowed,combinedTrendPoints} from '../src/features/topology/trendCompare.mjs';

test('area is visual configuration only and preserves old layout',()=>{
 const before=JSON.stringify(EMPTY_LAYOUT),area=addArea(EMPTY_LAYOUT,150,150);
 assert.equal(JSON.stringify(EMPTY_LAYOUT),before);
 assert.equal(area.areas.length,1);assert.deepEqual(area.symbols,[]);
 assert.deepEqual(area.wires,[]);assert.deepEqual(area.boxes,[]);
 assert.equal(Object.hasOwn(area.areas[0],'metric_codes'),false);
 assert.equal(Object.hasOwn(area.areas[0],'status'),false);
 assert.equal(removeArea(area,area.areas[0].id).areas.length,0);
});
test('area styling, drag, resize, opacity and locked position',()=>{
 let layout=addArea(EMPTY_LAYOUT,90,50),id=layout.areas[0].id;
 layout=patchArea(layout,id,{border:'solid',color:'amber',opacity:25,w:680,h:370,x:750,y:550});
 const a=layout.areas[0];
 assert.equal(a.border,'solid');assert.equal(a.color,'amber');assert.equal(a.opacity,25);
 assert.equal(a.w,680);assert.equal(a.h,370);assert.equal(a.x,750);assert.equal(a.y,550);
 assert.ok(layout.canvas.w>=a.x+a.w);assert.ok(layout.canvas.h>=a.y+a.h);
 const oldW=layout.canvas.w;
 layout=patchArea(layout,id,{locked:true});layout=patchArea(layout,id,{x:1200});
 assert.equal(layout.areas[0].x,750);assert.ok(layout.canvas.w>=oldW);
 layout=patchArea(layout,id,{border:'anything',opacity:77,color:'#fff'});
 assert.equal(layout.areas[0].border,'solid');assert.equal(layout.areas[0].opacity,25);
});
test('auto expand large canvas and manual resize must preserve content',()=>{
 const layout=addArea(EMPTY_LAYOUT,1550,850);
 assert.ok(layout.canvas.w>1600);assert.ok(layout.canvas.h>900);
 const big=expandForRect(layout,9000,6000,300,400);
 assert.ok(big.canvas.w>=9300&&big.canvas.h>=6400);
 assert.equal(resizeCanvas(big,200,200),null);
 assert.equal(resizeCanvas(big,14000,9000).canvas.w,14000);
 assert.ok(contentBounds(big).maxX>1000);
});
test('near-edge move grows layout but extreme invalid coordinates still clamp',()=>{
 let layout=addMetricBox(EMPTY_LAYOUT,{metric_code:'beban_sistem_kw'});
 const id=layout.boxes[0].id;
 layout=place(layout,id,'box',1480,800);
 assert.ok(layout.canvas.w>1600&&layout.canvas.h>900);
 assert.equal(layout.boxes[0].x,1480);
 const tooFar=place(EMPTY_LAYOUT,id,'box',99999,99999);
 assert.deepEqual(tooFar,EMPTY_LAYOUT);
});
test('popup comparison requires identical units and preserves zeros/nulls',()=>{
 const series={series:{a:[{hour:0,value:0},{hour:1,value:null},{hour:2,value:5}],
  b:[{hour:0,value:3},{hour:2,value:7}]}};
 assert.equal(comparisonAllowed(['a','b'],{a:'kW',b:'kW'}),true);
 assert.equal(comparisonAllowed(['a','b'],{a:'kW',b:'Hz'}),false);
 assert.equal(comparisonAllowed(['a','b'],{a:'kW'}),false);
 const rows=combinedTrendPoints(series,['a','b']);
 assert.equal(rows.length,24);assert.equal(rows[0].a,0);assert.equal(rows[0].b,3);
 assert.equal(rows[1].a,null);assert.equal(rows[1].b,null);assert.equal(rows[23].a,null);
});
test('compact viewer and original 24h popup remain intact in source',()=>{
 const path=new URL('../src/features/topology/',import.meta.url);
 const toolbar=readFileSync(new URL('ViewerToolbar.tsx',path),'utf8');
 const popup=readFileSync(new URL('TrendDrawer.tsx',path),'utf8');
 const box=readFileSync(new URL('ParamBox.tsx',path),'utf8');
 assert.match(toolbar,/topo-compact-toolbar/);
 assert.match(popup,/topo-modal-backdrop/);
 assert.match(popup,/Bandingkan semua/);
 assert.match(box,/setActiveCode/);
});
