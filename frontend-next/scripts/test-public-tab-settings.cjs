const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
function load(file,requireFn=require){
 const moduleRef={exports:{}};
 const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,"../src",file),"utf8"),{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 vm.runInNewContext(code,{module:moduleRef,exports:moduleRef.exports,require:requireFn});
 return moduleRef.exports;
}
const settings=load("lib/public-tab-settings.ts");
for(const value of [undefined,null,true,1])assert.equal(settings.publicTabSettings({show_public_info:value}).info,true);
for(const value of [false,0])assert.equal(settings.publicTabSettings({show_public_offers:value}).offers,false);
assert.equal(settings.visiblePublicTab("info",{info:false,offers:true}),"matches");
assert.equal(settings.visiblePublicTab("offers",{info:true,offers:false}),"matches");
assert.equal(settings.visiblePublicTab("info",{info:true,offers:false}),"info");

// Render the actual public navigation and selected content, keeping unrelated
// presentation components out of this focused regression.
let selected="matches";
const {PublicCupView}=load("components/PublicCupView.tsx",name=>{
 if(name==="react")return {...React,useState:value=>React.useState(value==="matches"?selected:value)};
 if(name==="react/jsx-runtime")return require(name);
 if(name==="next/dynamic")return {default:()=>()=>React.createElement("div",null,"fixture-lazy-content")};
 if(name==="../lib/public-tab-settings")return settings;
 if(name==="../lib/cup-share-title")return load("lib/cup-share-title.ts");
 if(name==="@/lib/matchday")return {belongsToTeam:()=>false,cupMatches:()=>[],hasPlayoffs:()=>false,matchdayOrder:rows=>rows};
 if(name==="@/lib/use-match-weather")return {useMatchWeather:()=>()=>undefined};
 if(name==="@/lib/format")return {matchStatus:()=>"upcoming"};
 if(name==="@/lib/api"||name==="@/lib/placement-standings"||name==="@/lib/public-refresh")return {};
 if(name.startsWith("./"))return new Proxy({},{get:(_,key)=>()=>React.createElement("div",null,`fixture-${String(key)}`)});
 throw Error(`Unexpected import: ${name}`);
});
function render(info,offers,tab="matches"){
 selected=tab;
 return renderToStaticMarkup(React.createElement(PublicCupView,{publicKey:"cup",initialStandings:[],initialCup:{tournament:{id:1,name:"Cup",show_public_info:info,show_public_offers:offers},teams:[],groups:[],matches:[],brackets:[],venue_points:[]}}));
}
for(const info of [true,false])for(const offers of [true,false]){
 const html=render(info,offers);
 assert.equal(/<button[^>]*>Info<\/button>/.test(html),info);
 assert.equal(/<button[^>]*>Erbjudanden<\/button>/.test(html),offers);
 assert.match(html,/<button[^>]*aria-current="page"[^>]*>Matcher<\/button>/);
}
assert.match(render(undefined,undefined),/>Info<\/button>/);
assert.match(render(undefined,undefined),/>Erbjudanden<\/button>/);
assert.match(render(false,true,"info"),/<h2>Matcher<\/h2>/);
assert.doesNotMatch(render(false,true,"info"),/public-info-v3/);
assert.match(render(true,false,"offers"),/<h2>Matcher<\/h2>/);
assert.doesNotMatch(render(true,false,"offers"),/fixture-lazy-content/);
assert.match(render(true,false,"info"),/public-info-v3/);
assert.match(render(false,true,"offers"),/fixture-lazy-content/);
console.log("Public tab settings: persistence policy, independent buttons and immediate content fallback PASS");
