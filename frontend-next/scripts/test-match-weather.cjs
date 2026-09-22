const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const root=path.join(__dirname,'../src');
function load(file){
  if(file.endsWith('.css'))return {default:new Proxy({}, {get:(_,key)=>String(key)})};
  if(!path.extname(file))file+=fs.existsSync(file+'.tsx')?'.tsx':'.ts';
  const output=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const module={exports:{}};
  const req=name=>name.startsWith('.')?load(path.resolve(path.dirname(file),name)):name.startsWith('@/')?load(path.join(root,name.slice(2))):require(name);
  vm.runInNewContext(output,{require:req,exports:module.exports,module,process,console,URL,URLSearchParams,AbortController,setTimeout,clearTimeout,fetch:()=>{throw Error('Unexpected real request')}},{filename:file});
  return module.exports;
}
const weather=load(path.join(root,'lib/match-weather.ts'));
const now=Date.parse('2026-10-24T07:00:00Z');
const data={timezone:'Europe/Stockholm',hourly:{time:['2026-10-24T10:00','2026-10-24T15:00','2026-10-24T16:00'],temperature_2m:[12,17,null],weather_code:[3,0,null],precipitation_probability:[70,5,null],wind_speed_10m:[4,2,null]}};
const forecast=weather.parseHourlyForecast(data,'Örebro');
assert.equal(weather.weatherForKickoff(forecast,'2026-10-24T10:30',now).hour.temperature,12);
assert.equal(weather.weatherForKickoff(forecast,'2026-10-24T15:15',now).hour.temperature,17);
assert.equal(weather.weatherForKickoff(forecast,'2026-10-24T08:30:00Z',now).hour.temperature,12);
assert.equal(weather.weatherForKickoff(forecast,'2026-10-24T16:00',now).status,'missing');
assert.equal(weather.weatherForKickoff(forecast,'2026-11-24T10:00',now).status,'too-early');
assert.equal(weather.forecastAvailability('2026-10-24T10:00',Date.parse('2026-09-22T10:00Z')),'too-early');
assert.equal(weather.forecastAvailability('2026-10-24T10:00',Date.parse('2026-10-09T10:00Z')),'available');
assert.equal(weather.forecastAvailability('2026-10-24T10:00',Date.parse('2026-10-08T10:00Z')),'too-early');
assert.equal(weather.localHour('2026-10-25T00:30:00Z'),'2026-10-25T02:00');
assert.equal(weather.localHour('2026-10-25T01:30:00Z'),'2026-10-25T02:00');
assert.equal(weather.parseHourlyForecast({timezone:'invalid',hourly:data.hourly},'test').status,'error');
const {MatchCard}=load(path.join(root,'components/MatchCard.tsx'));
const match={id:1,home_source:'team:1',away_source:'team:2',scheduled_start:'2026-10-24T15:15',pitch_number:1};
const props={match,teams:[{id:1,name:'Mycket långt hemmalagsnamn'},{id:2,name:'Gästande lag'}],pitches:[{pitch_number:1,name:'Ekäng'}],index:0,showKits:false};
const render=f=>renderToStaticMarkup(React.createElement(MatchCard,{...props,weather:f}));
const html=render(weather.weatherForKickoff(forecast,match.scheduled_start,now));
assert.match(html,/Vid avspark · Örebro/);
assert.match(html,/17°/);assert.match(html,/Regnrisk 5%/);assert.match(html,/Vind 2 m\/s/);
assert.ok(html.indexOf('Ekäng')<html.indexOf('Vid avspark'));
assert.ok(!render(undefined).includes('Prognos:'));
assert.match(render({status:'too-early'}),/Prognos kommer närmare matchdagen/);
const incomplete=weather.parseHourlyForecast({hourly:{time:['2026-10-24T15:00'],temperature_2m:[0]}},'Örebro');
const sparse=render(weather.weatherForKickoff(incomplete,match.scheduled_start,now));
assert.match(sparse,/0°/);assert.ok(!sparse.includes('Regnrisk'));assert.ok(!sparse.includes('Vind '));

const {PublicCupView}=load(path.join(root,'components/PublicCupView.tsx'));
function renderCup(enabled){return renderToStaticMarkup(React.createElement(PublicCupView,{publicKey:'weather-test',initialStandings:[],initialCup:{tournament:{id:1,name:'Weather Cup',arena_address:'Örebro',start_date:'2026-10-24',show_public_weather_configured:1,show_public_weather:enabled},teams:props.teams,matches:[match],groups:[],pitches:props.pitches,brackets:[],offers:[],venue_points:[]}}));}
const enabledCup=renderCup(true);
assert.ok(!enabledCup.includes('public-default-weather'),'No weather panel above schedule');
assert.ok(enabledCup.includes('Hämtar matchprognos'),'Forecast belongs to each public match');
assert.ok(!renderCup(false).includes('Hämtar matchprognos'),'Organizer can disable all match forecasts');

(async()=>{
  const calls=[];
  const mock=async(url)=>{
    calls.push(String(url));
    return {ok:true,json:async()=>String(url).includes('geocoding')?{results:[{name:'Örebro',latitude:59.27,longitude:15.21,timezone:'Europe/Stockholm'},{name:'Orebro',latitude:58,longitude:14}]}:data};
  };
  const results=await Promise.all(Array.from({length:200},()=>weather.loadHourlyForecast('Örebro',now,mock)));
  assert.equal(calls.length,2,'200 match consumers share one geocoding and one hourly request');
  assert.ok(results.every(r=>r.status==='ready'));
  assert.match(calls[1],/hourly=/);assert.match(calls[1],/wind_speed_unit=ms/);
  await weather.loadHourlyForecast('Örebro',now+10000,mock);assert.equal(calls.length,2);
  await weather.loadHourlyForecast('Örebro',now+31*60000,mock);assert.equal(calls.length,4);
  let limited=0;
  const rateLimit=async()=>{limited++;return {ok:false,status:429}};
  assert.equal((await weather.loadHourlyForecast('Arena, Teststad',now,rateLimit)).status,'error');
  await weather.loadHourlyForecast('Arena, Teststad',now+1000,rateLimit);
  assert.equal(limited,1,'429 stops both fallback lookup and immediate retries');
  await weather.loadHourlyForecast('Arena, Teststad',now+61000,rateLimit);assert.equal(limited,2);
  const ambiguous=async()=>({ok:true,json:async()=>({results:[{name:'Testort',latitude:1,longitude:2},{name:'Testort',latitude:3,longitude:4}]})});
  assert.equal((await weather.loadHourlyForecast('Testort',now,ambiguous)).status,'missing');
  console.log('Match weather: kickoff, timezone, missing data, cards, caching and rate limits PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
