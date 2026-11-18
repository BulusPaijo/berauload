import test from 'node:test';import assert from 'node:assert/strict';
import {clusterPoints,colorAndShape,categoriesLegend,validPoint,quartiles,withinNearest,sharedURL} from '../src/features/substations/map/helpers.mjs';
import {feederStacks,scatterPairs,findingPareto,trendRows,readDensity,saveDensity,encodeCsv} from '../src/features/substations/analysis/chartHelpers.mjs';

test('grid marker clusters by projection without discarding points',()=>{
 const points=[{id:1,lat:2,lon:117},{id:2,lat:2.01,lon:117.01},{id:3,lat:3,lon:118}];
 const projection=(lat,lon)=>({x:lat*100,y:lon*100});
 const groups=clusterPoints(points,projection,54);
 assert.equal(groups.length,2);assert.equal(groups.flatMap(g=>g.members).length,3);
 assert.equal(clusterPoints(points,projection,1).length,3);
});
test('category color AND shape come from rule, unknown remains neutral',()=>{
 const rules=[{active:true,kind:'category',group_name:'Beban',code:'a',name:'A',color:'#123456',marker:'triangle'}];
 const p={category:{code:'a'},columns:{}};
 assert.deepEqual(colorAndShape(p,'category','Beban',rules),{color:'#123456',marker:'triangle'});
 assert.deepEqual(categoriesLegend(rules,'Beban')[0].marker,'triangle');
 assert.equal(colorAndShape(p,'category','Lain',rules).color,'#89949a');
});
test('tile-free map still has grid markers, coordinates validate',()=>{
 assert.equal(validPoint({lat:null,lon:117}),false);
 assert.equal(validPoint({lat:91,lon:117}),false);
 assert.equal(validPoint({lat:0,lon:0}),true);
 assert.equal(clusterPoints([{id:3,lat:0,lon:0}],()=>({x:0,y:0})).length,1);
});
test('shared filters navigate between map and analysis',()=>{
 const url=sharedURL('map','category=a&findings=x&findings=y');
 const params=new URLSearchParams(url);
 assert.equal(params.get('gardu_tab'),'map');assert.deepEqual(params.getAll('findings'),['x','y']);
});
test('pareto, feeder grouping and scatter never invent null values',()=>{
 const feeder=feederStacks({feeder_categories:[{feeder_id:1,category:'a',count:3}]},
   {feeders:[{id:1,name:'TJR'}]});assert.equal(feeder[0].a,3);
 assert.deepEqual(scatterPairs([{id:1,sessions:{P:0,M:5}},{id:2,sessions:{P:null,M:7}}],['P','M']),[{id:1,x:0,y:5}]);
 assert.equal(findingPareto([{code:'b',count:1},{code:'a',count:9}])[0].code,'a');
 assert.equal(trendRows([{day:'2026-11-01',session:'P',value:0}])[0].P,0);
 assert.equal(quartiles([null,0,10,20,30]).length,3);
 assert.equal(withinNearest([{id:1,lat:0,lon:0}],0,0)[0].distance_km,0);
});
test('density is stored per user and CSV blocks formula injection',()=>{
 const storage=new Map(),store={getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)};
 assert.equal(readDensity(store,12),'comfortable');saveDensity(store,12,'compact');
 assert.equal(readDensity(store,12),'compact');assert.equal(readDensity(store,13),'comfortable');
 assert.match(encodeCsv([{name:'=HYPERLINK("x")',value:0}]),/"'=HYPERLINK/);
});
