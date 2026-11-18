import test from 'node:test';
import assert from 'node:assert/strict';
import {headerPlan,orderColumns,columnsFromParams,mobileSections,garduTone} from '../src/features/substations/grid.mjs';
import {visitTable,describeChange,historyView,fmtValue} from '../src/features/substations/detail/visitTable.mjs';
import {dragCodes,orderedCodes} from '../src/features/substations/formulas/helpers.mjs';
import {findingSentence,findingText} from '../src/features/substations/ui/findingText.mjs';

const mk=rows=>rows.map(([code,name,scope,unit,order],i)=>({id:i+1,code,name,scope,unit,display_order:order,active:true}));
const SEED=mk([['I_R','Arus R','line','A',1],['I_S','Arus S','line','A',2],['I_T','Arus T','line','A',3],['I_N','Arus Netral','line','A',4],
 ['V_R0','Tegangan Rel R-0','substation','V',5],['V_S0','Tegangan Rel S-0','substation','V',6],['V_T0','Tegangan Rel T-0','substation','V',7],
 ['V_RS','Tegangan Rel R-S','substation','V',8],['V_ST','Tegangan Rel S-T','substation','V',9],['V_TR','Tegangan Rel T-R','substation','V',10],
 ['V_END_RN','Tegangan Ujung JTR R-N','substation','V',11],['V_END_SN','Tegangan Ujung JTR S-N','substation','V',12],['V_END_TN','Tegangan Ujung JTR T-N','substation','V',13],
 ['GROUND_TR','Grounding Trafo','substation','ohm',14],['GROUND_AR','Grounding Arester','substation','ohm',15]]);

test('tegangan rel dipisah F-N dan F-F, tiap kelompok gardu punya warna sendiri',()=>{
 const plan=headerPlan(orderColumns(columnsFromParams(SEED),2));
 const gardu=plan.filter(b=>b.line===0);
 assert.deepEqual(gardu.map(b=>[b.title,b.tone,b.span]),[['Tegangan Rel F-N','relfn',3],['Tegangan Rel F-F','relff',3],
  ['Tegangan Ujung JTR','ujung',3],['Grounding','ground',2]]);
 assert.deepEqual(gardu[0].cells.map(c=>c.sub),['R-0','S-0','T-0']);
 assert.deepEqual(gardu[1].cells.map(c=>c.sub),['R-S','S-T','T-R']);
 assert.ok(gardu.every(b=>b.cells.every(c=>c.tone===b.tone)));
 assert.equal(plan.filter(b=>b.line>0).every(b=>b.tone===''),true);           // jurusan keep their own tint
 assert.equal(garduTone({line:0,name:'Tegangan Rel R-N'}),'relfn');
 assert.equal(garduTone({line:0,name:'Tegangan Rel T-R'}),'relff');
 assert.equal(garduTone({line:1,name:'Tegangan Ujung JTR R-N'}),'');           // per-jurusan legacy stays per jurusan
 const mob=mobileSections(SEED,1).filter(s=>s.line===0);
 assert.deepEqual(mob.map(s=>[s.title,s.tone,s.rows.length]),[['Tegangan Rel F-N','relfn',3],['Tegangan Rel F-F','relff',3],
  ['Tegangan Ujung JTR','ujung',3],['Grounding','ground',2]]);
});

test('tabel nilai: baris jurusan, kolom R S T N, sel berubah ditandai dengan nilai lama; kosong bukan 0',()=>{
 const values=[{param_id:1,line_no:1,value:125,flag:null},{param_id:2,line_no:1,value:98,flag:null},{param_id:1,line_no:2,value:null,flag:'RUSAK'},
  {param_id:5,line_no:0,value:231,flag:null}];
 const t=visitTable(SEED,values,2,['Barat'],[{param_id:1,line_no:1,before:120,before_flag:null}]);
 assert.deepEqual(t.head.map(h=>[h.title,h.unit,h.cols.map(c=>c.sub)]),[['Arus','A',['R','S','T','Netral']]]);
 assert.deepEqual(t.head[0].cols.map(c=>c.phase),['R','S','T','N']);
 assert.deepEqual(t.rows.map(r=>r.label),['Barat','Jurusan 2']);
 const c=t.rows[0].cells[0];assert.equal(c.value,125);assert.equal(c.changed,true);assert.equal(c.before,120);
 assert.equal(t.rows[0].cells[2].value,null);assert.equal(fmtValue(null,null),'');assert.equal(fmtValue(0,null),'0');
 assert.equal(t.rows[1].cells[0].flag,'RUSAK');assert.equal(t.changedCount,1);
 assert.deepEqual(t.gardu.map(g=>g.tone),['relfn','relff','ujung','ground']);
 assert.equal(t.gardu[0].cells[0].value,231);
});

test('riwayat dalam bahasa manusia',()=>{
 const change={param_id:1,code:'I_R',name:'Arus R',unit:'A',line_no:1,before:120,before_flag:null,after:125,after_flag:null};
 assert.equal(describeChange(change),'Jurusan 1 · Arus R 120 → 125 A');
 assert.equal(describeChange({...change,line_no:0,name:'Tegangan Rel R-0',unit:'V',before:231,after:null}),'Tegangan Rel R-0 231 → kosong');
 assert.equal(describeChange({...change,after:null,after_flag:'RUSAK'},f=>f==='RUSAK'?'Alat rusak':f,['Barat']),'Barat · Arus R 120 → Alat rusak');
 const v=historyView([{id:9,at:'2034-01-02T02:00:00Z',user:'Administrator',kind:'save',actor_role:'admin_global',reason:null,
  revision_before:1,revision_after:2,summary:'Administrator mengubah 1 nilai',changes:[change],meta:[]},
  {id:8,at:'2034-01-02T01:00:00Z',user:'Administrator',kind:'create',actor_role:'admin_global',reason:null,revision_before:null,revision_after:1,
   summary:'Administrator membuat pengukuran dengan 1 nilai',changes:[change],meta:[]}]);
 assert.deepEqual(v.map(e=>[e.tone,e.revision,e.lines.length]),[['edit',2,1],['new',1,0]]);
 assert.equal(v[0].lines[0],'Jurusan 1 · Arus R 120 → 125 A');
});

test('urutan kategori: seret dan panah',()=>{
 const rows=[{id:1,code:'a',display_order:1},{id:2,code:'b',display_order:2},{id:3,code:'c',display_order:3},{id:4,code:'d',display_order:4}];
 assert.deepEqual(dragCodes(rows,'d','b'),['a','d','b','c']);
 assert.deepEqual(dragCodes(rows,'a','c'),['b','c','a','d']);
 assert.deepEqual(dragCodes(rows,'a','a'),['a','b','c','d']);
 assert.deepEqual(orderedCodes(rows,'b',-1),['b','a','c','d']);
});

test('kalimat contoh temuan: ATAU untuk salah satu, DAN untuk semua',()=>{
 assert.equal(findingText(['Tak seimbang','Netral tinggi'],'any'),'Gardu dengan Tak seimbang ATAU Netral tinggi — cukup satu temuan saja yang cocok.');
 assert.equal(findingText(['Tak seimbang','Netral tinggi'],'all'),'Gardu dengan Tak seimbang DAN Netral tinggi — gardu harus punya semua temuan ini sekaligus.');
 assert.equal(findingText(['Tak seimbang'],'all'),'Gardu dengan Tak seimbang');
 assert.equal(findingSentence([],'any').parts.length,0);
});
