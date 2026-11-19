import test from 'node:test';
import assert from 'node:assert/strict';
import {rangeText,ageText,excludedLines,splitOptions,clampPortion,sliderState,sideRows,linesRows,planSummary,canApply,pct} from '../src/features/substations/advice/adviceView.mjs';

const ev=(persen,kva,code)=>({persen,beban_kva:kva,overload:persen>100,category:{code,name:code.toUpperCase(),color:'#000'}});
const side={id:1,code:'P1',name:'Gardu P1',kva_before:100,kva_after:200,phase_before:3,phase_after:3,before:ev(124.7,124.7,'overload'),after:ev(62.4,124.7,'normal'),
 lines_before:[{line_no:1,i_r:100,i_s:100,i_t:100,i_n:5},{line_no:2,i_r:80,i_s:80,i_t:null,i_n:null}],lines_after:[{line_no:1,i_r:100,i_s:100,i_t:100,i_n:5},{line_no:2,i_r:80,i_s:80,i_t:null,i_n:null}]};

test('rentang porsi dan persen ditulis jelas; kosong tetap kosong, bukan 0',()=>{
 assert.equal(rangeText({feasible:true,p_min:36,p_max:44}),'36%–44%');
 assert.equal(rangeText({feasible:true,p_min:50,p_max:50}),'50%');
 assert.equal(rangeText({feasible:false,p_min:60,p_max:40}),'');
 assert.equal(pct(null),'—');assert.equal(pct(undefined),'—');assert.match(pct(0),/^0,0%$/);
 assert.equal(ageText(0),'hari ini');assert.equal(ageText(12),'12 hari lalu');assert.equal(ageText(null),'');
});
test('opsi layak dipisah dari yang belum memenuhi tanpa mengubah urutan server',()=>{
 const r=splitOptions([{feasible:true,id:1},{feasible:false,id:2},{feasible:true,id:3}]);
 assert.deepEqual(r.ok.map(o=>o.id),[1,3]);assert.deepEqual(r.no.map(o=>o.id),[2]);
 assert.deepEqual(splitOptions(undefined),{ok:[],no:[]});
});
test('penggeser porsi dibatasi 1–100 dan memberi tanda di dalam/ di luar rentang layak',()=>{
 assert.equal(clampPortion('250'),100);assert.equal(clampPortion(-5),1);assert.equal(clampPortion('abc',{p_min:36}),36);assert.equal(clampPortion(40.6),41);
 const opt={feasible:true,p_min:36,p_max:44};
 assert.deepEqual(sliderState(40,opt),{inside:true,tone:'ok'});assert.deepEqual(sliderState(30,opt),{inside:false,tone:'bad'});
 assert.deepEqual(sliderState(40,{feasible:false}),{inside:false,tone:'bad'});assert.deepEqual(sliderState(40,null),{inside:false,tone:'bad'});
});
test('tabel sebelum/sesudah menandai baris yang berubah',()=>{
 const rows=Object.fromEntries(sideRows(side).map(r=>[r.label,r]));
 assert.equal(rows['Kapasitas trafo'].changed,true);assert.equal(rows['Kapasitas trafo'].after,'200 kVA');
 assert.equal(rows['Beban'].changed,false);                                   // same current, bigger trafo
 assert.equal(rows['Kategori'].before,'OVERLOAD');assert.equal(rows['Kategori'].changed,true);
 const l=linesRows(side);assert.equal(l[0].before,100);assert.equal(l[1].before,null);   // missing phase -> NULL, never 0
});
test('alasan pengecualian dan ringkasan rencana',()=>{
 assert.deepEqual(excludedLines({tanpa_koordinat:2,tanpa_pengukuran:0,tidak_dapat_dinilai:1}),['2 gardu tanpa koordinat','1 gardu arus belum lengkap']);
 assert.deepEqual(excludedLines(undefined),[]);
 assert.equal(planSummary({kind:'swap',target_code:'Q1'}),'Tukar trafo dengan Q1');
 assert.equal(planSummary({kind:'move',target_code:'Q2',line_no:1,portion:40}),'Pindah 40% jurusan 1 ke Q2');
 assert.equal(planSummary(null),'');
});
test('tombol terapkan ke master hanya untuk tukar trafo selesai yang belum diterapkan dan pemegang hak master',()=>{
 const f={type_code:'tukar_trafo',status:'selesai',plan:{kind:'swap',applied:null}};
 assert.equal(canApply(f,true),true);assert.equal(canApply(f,false),false);
 assert.equal(canApply({...f,status:'dikerjakan'},true),false);
 assert.equal(canApply({...f,plan:{kind:'swap',applied:{on:'x'}}},true),false);
 assert.equal(canApply({...f,type_code:'pindah_beban',plan:{kind:'move',applied:null}},true),false);
 assert.equal(canApply({type_code:'tukar_trafo',status:'selesai',plan:null},true),false);
});
