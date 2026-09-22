const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const root = path.join(__dirname,'../src');
const DRAW='Oavgjort tillåtet – tabell avgör';
let adminData;
let firstState;
function load(file) {
  if(file.endsWith('.css'))return {default:new Proxy({}, {get:(_,key)=>String(key)})};
  if(!path.extname(file))file+=fs.existsSync(file+'.tsx')?'.tsx':'.ts';
  const source=fs.readFileSync(file,'utf8');
  const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const module={exports:{}};
  const requireModule=name=>{
    if(name==='react' && file.endsWith('playoff-admin.tsx'))return {...React,useState:value=>{const state=firstState?adminData:value;firstState=false;return [state,()=>{}]},useEffect:()=>{},useCallback:fn=>fn};
    if(name.startsWith('.'))return load(path.resolve(path.dirname(file),name));
    if(name.startsWith('@/'))return load(path.join(root,name.slice(2)));
    return require(name);
  };
  vm.runInNewContext(output,{require:requireModule,exports:module.exports,module,process,console,fetch:()=>{throw Error('Unexpected request')}},{filename:file});
  return module.exports;
}
const {default:PlayoffAdmin}=load(path.join(root,'components/playoff-admin.tsx'));
function render(rule){
  firstState=true;
  adminData={playoff_format:'Manuellt slutspel',playoff_tie_rule:rule,playoff_extra_time_minutes:0,
    placement_mode:rule===DRAW,placement_eligible:true,placement_groups:[],structure_locked:true,played_count:0,
    bronze_match:rule!==DRAW,bracket_ready:true,bracket_validation:{ready:true,issue_count:0,issues:[]},
    brackets:[{id:1,name:'Importerat slutspel',size:9,bronze_match:rule!==DRAW,matches:[{
      id:10,stage:'GULDGRUPPEN',home_source:'group:54:1',away_source:'group:56:1',
      home_source_label:'1:a i grupp A',away_source_label:'1:a i grupp C',scheduled_start:'2026-10-24T14:30'
    }]}]};
  return renderToStaticMarkup(React.createElement(PlayoffAdmin,{token:'test',cupId:1}));
}
const old=render('Straffar direkt');
assert.ok(old.includes(`<option>${DRAW}</option>`), 'Existing imported cups must offer the draw option');
const selected=render(DRAW);
assert.ok(selected.includes(`<option selected="">${DRAW}</option>`));
assert.ok(selected.includes('Placeringsgruppspel'));
assert.ok(selected.includes('1:a i grupp A'));
assert.ok(!selected.includes('grupp 54'));
assert.ok(!selected.includes('type="checkbox"'), 'No bronze checkbox in placement mode');
assert.ok(!selected.includes('16 platser'));
assert.match(selected,/<strong>1:a i grupp A.*?<\/strong><span>GULDGRUPPEN<\/span><small>/);
const {PlacementTables}=load(path.join(root,'components/PlacementTables.tsx'));
const html=renderToStaticMarkup(React.createElement(PlacementTables,{groups:[{name:'GULDGRUPPEN',bracket_id:1,placement:1,rows:[],winner:null,complete:false,ranking_tied:false}]}));
assert.ok(html.includes('preliminär'));
assert.ok(!html.includes('Cupvinnare:'));
console.log('Placement playoff UI: PASS');
