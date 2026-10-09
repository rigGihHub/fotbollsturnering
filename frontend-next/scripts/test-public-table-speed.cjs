const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const React=require('react');
const compile=file=>ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src',file),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
function library(file,globals={}){const m={exports:{}};vm.runInNewContext(compile(file),{module:m,exports:m.exports,require,...globals});return m.exports;}
const refreshPolicy=library('lib/public-refresh.ts');
const group={id:1,name:'Grupp A'};
const rows=points=>[{position:1,team_id:1,Lag:'Lag A',S:points?1:0,V:points?1:0,O:0,F:0,MS:points?1:0,P:points}];
const snapshot=points=>({tournament:{id:1,name:'Cup',show_public_info:false,show_public_offers:false},teams:[{id:1,name:'Lag A',group_id:1}],groups:[group],matches:[{id:1,match_status:points?'finished':'not_started',home_score:points?1:null}],brackets:[],venue_points:[],standings:[{group,rows:rows(points)}]});
function harness(initialCup){
 let slots=[],index=0,dirty=true,tree,effects=[],timers=new Map(),nextTimer=0,tableCalls=0,cupCalls=0,fresh=snapshot(3),fail=false,scrolls=0,hold=null;
 const listeners=new Map();
 const same=(a,b)=>a&&b&&a.length===b.length&&a.every((v,i)=>Object.is(v,b[i]));
 const hooks={...React,
  useState:init=>{const i=index++;if(!slots[i])slots[i]={value:typeof init==='function'?init():init};return [slots[i].value,value=>{const v=typeof value==='function'?value(slots[i].value):value;if(!Object.is(v,slots[i].value)){slots[i].value=v;dirty=true;}}];},
  useRef:value=>{const i=index++;return (slots[i]??={current:value});},
  useMemo:(fn,deps)=>{const i=index++;if(!same(slots[i]?.deps,deps))slots[i]={deps,value:fn()};return slots[i].value;},
  useEffect:(fn,deps)=>{const i=index++;if(!same(slots[i]?.deps,deps)){const prior=slots[i];slots[i]={deps};effects.push(()=>{prior?.cleanup?.();slots[i].cleanup=fn();});}},
 };
 const windowRef={setTimeout:(fn,delay)=>{timers.set(++nextTimer,{fn,delay});return nextTimer;},clearTimeout:id=>timers.delete(id),scrollTo:()=>{scrolls++;},addEventListener:(event,fn)=>listeners.set(event,fn),removeEventListener:event=>listeners.delete(event)};
 const settings=library('lib/public-tab-settings.ts',{window:windowRef});
 const moduleRef={exports:{}};
 vm.runInNewContext(compile('components/PublicCupView.tsx'),{module:moduleRef,exports:moduleRef.exports,Date,document:{title:'',visibilityState:'visible',addEventListener(){},removeEventListener(){}},window:windowRef,localStorage:{getItem(){return null;}},require:name=>{
  if(name==='react')return hooks;
  if(name==='react/jsx-runtime')return require(name);
  if(name==='next/dynamic')return {default:()=>()=>null};
  if(name==='../lib/public-tab-settings')return settings;
  if(name==='../lib/cup-share-title')return {cupShareTitle:name=>name};
  if(name==='@/lib/matchday')return {cupMatches:cup=>cup.matches,hasPlayoffs:()=>false,matchdayOrder:rows=>rows,belongsToTeam:()=>true};
  if(name==='@/lib/use-match-weather')return {useMatchWeather:()=>()=>undefined};
  if(name==='@/lib/format')return {matchStatus:m=>m.match_status==='finished'?'done':'upcoming'};
  if(name==='@/lib/match-competition-label')return library('lib/match-competition-label.ts');
  if(name==='@/lib/placement-standings')return {placementStandingsPresentation:()=>undefined};
  if(name==='@/lib/public-refresh')return refreshPolicy;
  if(name==='@/lib/api')return {CupNaviApiError:class extends Error{},getStandings:async()=>{tableCalls++;return {groups:[{group,rows:rows(0)}]};},getCup:async()=>{cupCalls++;if(fail)throw Error('offline');const result=fresh;if(hold){const pending=hold;hold=null;await pending;}return result;}};
  if(name==='./TextTvStandings')return {TextTvStandings:'Standings'};
  if(name.startsWith('./'))return new Proxy({},{get:(_,key)=>String(key)});
  throw Error(`Unexpected import ${name}`);
 }});
 const render=()=>{let guard=0;while(dirty){assert.ok(++guard<20,'render settles');dirty=false;index=0;tree=moduleRef.exports.PublicCupView({publicKey:'cup',initialCup,initialStandings:[]});const pending=effects;effects=[];pending.forEach(fn=>fn());}return tree;};
 const nodes=(node,out=[])=>{if(!node||typeof node!=='object')return out;if(Array.isArray(node)){node.forEach(n=>nodes(n,out));return out;}out.push(node);nodes(node.props?.children,out);return out;};
 const click=label=>{nodes(tree).find(n=>n.type==='button'&&n.props.children===label).props.onClick();render();};
 const timer=async delay=>{const entry=[...timers].find(([,v])=>v.delay===delay);assert.ok(entry,`timer ${delay} exists`);timers.delete(entry[0]);await entry[1].fn();await new Promise(setImmediate);render();};
 const flush=async()=>{await new Promise(setImmediate);render();};
 render();return {render,click,timer,flush,nodes:()=>nodes(tree),table:()=>nodes(tree).find(n=>n.type==='Standings'),counts:()=>({tableCalls,cupCalls,scrolls}),offline:()=>{fail=true;},setFresh:value=>{fresh=value;},holdNext:()=>{let resolve;hold=new Promise(done=>{resolve=done;});return ()=>resolve();},saved:cupId=>{listeners.get('storage')?.({key:'cupnavi:public-cup-update',newValue:JSON.stringify({cupId})});}};
}
(async()=>{
 const current=harness(snapshot(0));
 current.click('Tabeller');assert.equal(current.table().props.rows[0].P,0);
 current.click('Matcher');current.click('Tabeller');
 assert.deepEqual(current.counts(),{tableCalls:0,cupCalls:0,scrolls:0},'first and repeated tab clicks use snapshot without network or scroll');
 await current.timer(120000);
 assert.equal(current.table().props.rows[0].P,3,'background refresh replaces table from authoritative fresh cup');
 assert.equal(current.counts().tableCalls,0,'refresh needs no separate standings request');
 current.offline();await current.timer(120000);
 assert.equal(current.table().props.rows[0].P,3,'network failure retains visible rows');
 const old=snapshot(0);delete old.standings;
 const legacy=harness(old);await legacy.timer(700);legacy.click('Tabeller');
 assert.equal(legacy.table().props.rows[0].P,0);legacy.click('Matcher');legacy.click('Tabeller');
 assert.equal(legacy.counts().tableCalls,1,'older API is warmed once, not once per tab click');
 const empty=snapshot(0);empty.standings=[];
 const noTables=harness(empty);noTables.click('Tabeller');
 assert.equal(noTables.table(),undefined);assert.equal(noTables.counts().tableCalls,0,'empty authoritative tables do not refetch forever');

 const stale=snapshot(0);stale.tournament.show_public_info=true;stale.tournament.show_public_offers=true;
 const opening=harness(stale);
 const hasButton=(view,label)=>view.nodes().some(node=>node.type==='button'&&node.props.children===label);
 assert.ok(hasButton(opening,'Info')&&hasButton(opening,'Erbjudanden'));
 await opening.timer(1500);
 assert.ok(!hasButton(opening,'Info')&&!hasButton(opening,'Erbjudanden'),'opening sync replaces cached tab settings without waiting two minutes');
 opening.click('Tabeller');await opening.timer(1500);
 assert.equal(opening.counts().cupCalls,1,'switching tabs does not repeat opening synchronization');

 const saved=harness(stale);saved.setFresh(stale);
 const release=saved.holdNext();saved.saved(1);
 assert.equal(saved.counts().cupCalls,1);
 saved.setFresh(snapshot(3));saved.saved(2);saved.saved(1);
 assert.equal(saved.counts().cupCalls,1,'save during an in-flight refresh queues rather than overlaps');
 release();await saved.flush();
 assert.equal(saved.counts().cupCalls,2,'save is reread after the older request completes');
 assert.ok(!hasButton(saved,'Info')&&!hasButton(saved,'Erbjudanden'));
 saved.saved(2);await saved.flush();assert.equal(saved.counts().cupCalls,2,'another cup save is ignored');
 console.log('Public tables: instant first/repeated clicks, one-snapshot refresh, offline retention, legacy fallback and authoritative empty state PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
