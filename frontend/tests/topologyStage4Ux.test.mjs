import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {EMPTY_LAYOUT,clone} from '../src/features/topology/editorState.mjs';
import {addSymbol,patchSymbol,addWire} from '../src/features/topology/stage4State.mjs';

test('busbar length may change without changing reading data, circuits or previous snapshot',()=>{
 const original=addWire(addSymbol(EMPTY_LAYOUT,'busbar',80,60),[[10,10],[100,10]]);
 const symbol=original.symbols[0];
 const output=patchSymbol(original,symbol.id,{w:530});
 assert.equal(output.symbols[0].w,530);
 assert.equal(output.symbols[0].x,80);
 assert.deepEqual(output.wires,original.wires);
 assert.equal(original.symbols[0].w,180);
 assert.equal(Object.hasOwn(output.symbols[0],'value'),false);
});
test('busbar dimension keeps grid and remains inside canvas',()=>{
 let layout=addSymbol(EMPTY_LAYOUT,'busbar',1380,30);
 const id=layout.symbols[0].id;
 layout=patchSymbol(layout,id,{w:1200});
 assert.equal(layout.symbols[0].w,220);
 assert.ok(layout.symbols[0].x+layout.symbols[0].w<=1600);
 assert.equal(layout.symbols[0].w%10,0);
 layout=patchSymbol(layout,id,{w:51});
 assert.equal(layout.symbols[0].w,50);
 layout=patchSymbol(layout,id,{w:-10});
 assert.equal(layout.symbols[0].w,40);
});
test('non-busbar symbols ignore width changes',()=>{
 const layout=addSymbol(EMPTY_LAYOUT,'breaker',100,100);
 const edited=patchSymbol(layout,layout.symbols[0].id,{w:800});
 assert.equal(edited.symbols[0].w,120);
 assert.deepEqual(layout.symbols[0],clone(layout).symbols[0]);
});
test('topology has isolated full-width workspace and visible parameter search',()=>{
 const css=readFileSync(new URL('../src/features/topology/topology.css',import.meta.url),'utf8');
 const prop=readFileSync(new URL('../src/features/topology/PropertiesPanel.tsx',import.meta.url),'utf8');
 assert.match(css,/\.workspace-topology \.content-topology\{max-width:none/);
 assert.match(css,/\.shell\.topology-focus \.sidebar\{display:none\}/);
 assert.match(css,/\.topo-selected-metrics\{max-height:175px;overflow-y:auto/);
 assert.match(prop,/Cari parameter/);
});
