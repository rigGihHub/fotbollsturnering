"use client";

import {FormEvent,useCallback,useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";
import {reporterSessionDeadline} from "../lib/reporter-session";
import {QUEUE_EVENT,SYNC_REQUEST_EVENT,appendReporterMutation,completeReporterResultMutation,isNetworkError,isResultMutation,isResultOrStatusMutation,isStatusMutation,pendingReporterCount,readReporterCache,readReporterQueue,removeReporterMutation,updateReporterMutation,upsertReporterMutation,writeReporterCache} from "../lib/reporter-offline";
import ReporterMatchEvents from "./reporter-match-events";
import ReporterNavigation from "./reporter-navigation";

const API=CLIENT_API_BASE,KEY="cupnavi_reporter_session_v1",SESSION_CACHE="session";
// Rollgräns: Cupinställningar är inte åtkomliga här; rapportören kan bara arbeta med matchdata.
type Cup={id:number;name:string;public_slug?:string|null};
type MatchLifecycle="not_started"|"live"|"halftime"|"finished";
type ReporterSettings={scorers:boolean;assists:boolean;cards:boolean;fairness:boolean;minutes_per_half:number;halves:number};
type Match={requires_winner?:boolean;id:number;stage?:string|null;home_team:string;away_team:string;home_score:number|null;away_score:number|null;home_penalties?:number|null;away_penalties?:number|null;status:string;match_status?:MatchLifecycle|null;scheduled_start?:string|null;clock_elapsed_seconds?:number;actual_started_at?:string|null};
type CachedSession={cup:Cup;matches:Match[];settings?:ReporterSettings};
const DEFAULT_SETTINGS:ReporterSettings={scorers:true,assists:true,cards:true,fairness:false,minutes_per_half:20,halves:2};
const lifecycle=(match:Match):MatchLifecycle=>match.match_status==="live"||match.match_status==="halftime"||match.match_status==="finished"?match.match_status:match.status==="played"?"finished":"not_started";
const isAuthFailure=(error:unknown)=>/(401|session|inloggning krävs|ogiltig|gått ut|authentication)/i.test(error instanceof Error?error.message:String(error));

async function call<T>(path:string,token?:string|null,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);if(token)headers.set("Authorization",`Bearer ${token}`);if(init.body)headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);return payload as T;
}

export default function ReporterClient(){
 const[code,setCode]=useState("");
 const[matchQuery,setMatchQuery]=useState("");
 const[includeFinished,setIncludeFinished]=useState(false);
 const[token,setToken]=useState<string|null>(null),[cupInfo,setCupInfo]=useState<Cup|null>(null),[matches,setMatches]=useState<Match[]>([]),[settings,setSettings]=useState<ReporterSettings>(DEFAULT_SETTINGS);
 const[busy,setBusy]=useState(false),[syncing,setSyncing]=useState(false),[online,setOnline]=useState(true),[pending,setPending]=useState(0);
 const[focusMatchId,setFocusMatchId]=useState<number|null>(null);
 const[error,setError]=useState(""),[message,setMessage]=useState("");
 const logout=useCallback(()=>{localStorage.removeItem(KEY);setToken(null);setCupInfo(null);setMatches([]);setMessage("");setError("")},[]);
 const remember=useCallback((nextCup:Cup,nextMatches:Match[],nextSettings=settings)=>writeReporterCache<CachedSession>(SESSION_CACHE,{cup:nextCup,matches:nextMatches,settings:nextSettings}),[settings]);
 const load=useCallback(async(sessionToken:string)=>{
  const[session,reporting]=await Promise.all([call<{cup:Cup}>("/api/reporter/session",sessionToken),call<{matches:Match[];settings?:ReporterSettings}>("/api/reporter/reporting",sessionToken)]);
  const next=reporting.matches||[], nextSettings={...DEFAULT_SETTINGS,...(reporting.settings||{})};setCupInfo(session.cup);setMatches(next);setSettings(nextSettings);remember(session.cup,next,nextSettings);
 },[remember]);
 useEffect(()=>{if(!matches.length){setFocusMatchId(null);return}setFocusMatchId(current=>current&&matches.some(match=>match.id===current)?current:(matches.find(match=>["live","halftime"].includes(lifecycle(match)))||matches.find(match=>lifecycle(match)!=="finished")||matches[0]).id)},[matches]);

 useEffect(()=>{
  const refresh=()=>{setOnline(navigator.onLine);setPending(pendingReporterCount(cupInfo?.id))};refresh();
  window.addEventListener("online",refresh);window.addEventListener("offline",refresh);window.addEventListener(QUEUE_EVENT,refresh);
  return()=>{window.removeEventListener("online",refresh);window.removeEventListener("offline",refresh);window.removeEventListener(QUEUE_EVENT,refresh)};
 },[cupInfo?.id]);
 useEffect(()=>{
  const queryCup=new URLSearchParams(window.location.search).get("cup");
  const stored=localStorage.getItem(KEY);if(!stored)return;setToken(stored);
  const cached=readReporterCache<CachedSession>(SESSION_CACHE),cacheMatchesLink=!queryCup||queryCup===cached?.cup.public_slug||queryCup===String(cached?.cup.id);
  if(cached&&cacheMatchesLink){setCupInfo(cached.cup);setMatches(cached.matches);setSettings({...DEFAULT_SETTINGS,...(cached.settings||{})})}
  void load(stored).catch(reason=>{if(isAuthFailure(reason)){logout();return}if(cached&&cacheMatchesLink){setMessage(navigator.onLine?"Sparad vy visas medan CupNavi återansluter.":"Offline: senast hämtade matcher visas.");return}logout()});
 },[load,logout]);

 useEffect(()=>{
  if(!token)return;
  let timer:number|undefined;
  const checkExpiry=()=>{
   window.clearTimeout(timer);
   const remaining=reporterSessionDeadline(token)-Date.now();
   if(remaining<=0){logout();setError("Koden har gått ut. Be arrangören om en ny kod.");return}
   timer=window.setTimeout(checkExpiry,Math.min(remaining,72*60*60*1000));
  };
  checkExpiry();window.addEventListener("focus",checkExpiry);
  return()=>{window.clearTimeout(timer);window.removeEventListener("focus",checkExpiry)};
 },[logout,token]);

 const flushResults=useCallback(async()=>{
  if(!token||!cupInfo||!navigator.onLine||syncing)return;const queued=readReporterQueue().filter(isResultOrStatusMutation).filter(item=>item.cupId===cupInfo.id&&item.state!=="conflict").sort((a,b)=>a.createdAt-b.createdAt);if(!queued.length)return;
  setSyncing(true);
  try{
   const reporting=await call<{matches:Match[];settings?:ReporterSettings}>("/api/reporter/reporting",token);let serverMatches=reporting.matches||[];
   for(const mutation of queued){
    const current=serverMatches.find(item=>item.id===mutation.matchId);if(!current){updateReporterMutation(mutation.id,{state:"conflict"});continue}
    if(isResultMutation(mutation)){
     const desired=current.home_score===mutation.payload.home_score&&current.away_score===mutation.payload.away_score&&(current.home_penalties??null)===mutation.payload.home_penalties&&(current.away_penalties??null)===mutation.payload.away_penalties;
     if(desired){completeReporterResultMutation(mutation);continue}
     const unchanged=current.home_score===mutation.payload.expected_home_score&&current.away_score===mutation.payload.expected_away_score&&(current.home_penalties??null)===mutation.payload.expected_home_penalties&&(current.away_penalties??null)===mutation.payload.expected_away_penalties;
     if(!unchanged){updateReporterMutation(mutation.id,{state:"conflict"});setError("En offlineändring krockar med ett nyare serverresultat och har inte skrivits över.");continue}
     await call(`/api/reporter/reporting/matches/${mutation.matchId}`,token,{method:"PUT",body:JSON.stringify(mutation.payload)});completeReporterResultMutation(mutation);
     serverMatches=serverMatches.map(item=>item.id===mutation.matchId?{...item,home_score:mutation.payload.home_score,away_score:mutation.payload.away_score,home_penalties:mutation.payload.home_penalties,away_penalties:mutation.payload.away_penalties}:item);
    }else{
     const currentStatus=lifecycle(current);
     if(currentStatus===mutation.payload.status){removeReporterMutation(mutation.id);continue}
     if(currentStatus!==mutation.payload.expected_status){updateReporterMutation(mutation.id,{state:"conflict"});setError("En statusändring krockar med en nyare matchstatus och har stoppats.");continue}
     await call(`/api/reporter/reporting/matches/${mutation.matchId}/status`,token,{method:"PUT",body:JSON.stringify(mutation.payload)});removeReporterMutation(mutation.id);
     serverMatches=serverMatches.map(item=>item.id===mutation.matchId?{...item,match_status:mutation.payload.status,status:mutation.payload.status==="finished"?"played":mutation.payload.status}:item);
    }
   }
   await load(token);setMessage(pendingReporterCount(cupInfo.id)?"Vissa ändringar väntar fortfarande. Kontrollera meddelandet ovan.":"Alla ändringar är sparade på servern.");
  }catch(reason){if(!isNetworkError(reason))setError(reason instanceof Error?reason.message:"Offlinekön kunde inte synkroniseras.")}
  finally{setSyncing(false);setPending(pendingReporterCount(cupInfo.id))}
 },[cupInfo,load,syncing,token]);
 useEffect(()=>{if(!online||pending===0)return;const retry=window.setTimeout(()=>void flushResults(),500);return()=>window.clearTimeout(retry)},[online,pending,flushResults]);

 async function login(event:FormEvent){event.preventDefault();setBusy(true);setError("");try{const result=await call<{token:string;cup:Cup}>("/api/reporter/session",null,{method:"POST",body:JSON.stringify({code})});localStorage.setItem(KEY,result.token);setToken(result.token);setCupInfo(result.cup);setCode("");await load(result.token)}catch(reason){setError(reason instanceof Error?reason.message:"Inloggningen misslyckades.")}finally{setBusy(false)}}
 function optimisticResult(match:Match,payload:{home_score:number;away_score:number;home_penalties:number|null;away_penalties:number|null}){
  setMatches(current=>{const next=current.map(item=>item.id===match.id?{...item,...payload,status:"played"}:item);if(cupInfo)remember(cupInfo,next);return next});
 }
 function save(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string){
  if(!token||!cupInfo)return;const payload={home_score:Number(home),away_score:Number(away),home_penalties:homePenalties===""?null:Number(homePenalties),away_penalties:awayPenalties===""?null:Number(awayPenalties),expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null};
  const mutation={id:`result-${cupInfo.id}-${match.id}`,kind:"result" as const,cupId:cupInfo.id,matchId:match.id,createdAt:Date.now(),state:"queued" as const,payload};setError("");setMessage("");
  upsertReporterMutation(mutation);optimisticResult(match,payload);setMessage(navigator.onLine?"Registrerat – synkroniserar med servern.":"Sparat lokalt. Resultatet skickas när nätet är tillbaka och stäms av mot servern.");
 }
 function changeScore(match:Match,side:"home"|"away",delta:number){
  const home=Math.max(0,(match.home_score??0)+(side==="home"?delta:0)),away=Math.max(0,(match.away_score??0)+(side==="away"?delta:0));
  if(home===(match.home_score??0)&&away===(match.away_score??0))return;
  save(match,String(home),String(away),match.home_penalties==null?"":String(match.home_penalties),match.away_penalties==null?"":String(match.away_penalties));
  if(delta>0&&typeof navigator.vibrate==="function")navigator.vibrate(25);
 }
 function changeStatus(match:Match,next:MatchLifecycle){
  if(!cupInfo)return;const current=lifecycle(match);
  if(next==="finished"){
   if((match.requires_winner??(match.stage!=="Gruppspel"))&&(match.home_score??0)===(match.away_score??0)&&match.home_penalties==null){setError("En oavgjord slutspelsmatch måste avgöras innan den avslutas.");return}
   if(!window.confirm(`Avsluta ${match.home_team} – ${match.away_team}?`))return;
   if(match.home_score==null||match.away_score==null)save(match,String(match.home_score??0),String(match.away_score??0),"","");
  }
  const mutation={id:`status-${cupInfo.id}-${match.id}-${Date.now()}-${next}`,kind:"status" as const,cupId:cupInfo.id,matchId:match.id,createdAt:Date.now()+1,state:"queued" as const,payload:{status:next,expected_status:current}};
  appendReporterMutation(mutation);setMatches(rows=>{const updated=rows.map(item=>item.id===match.id?{...item,match_status:next,status:next==="finished"?"played":next,actual_started_at:next==="live"?new Date().toISOString():null}:item);remember(cupInfo,updated);return updated});setError("");setMessage(navigator.onLine?"Matchstatus uppdaterad – synkroniserar.":"Matchstatus sparad lokalt och skickas när nätet är tillbaka.");
 }
 const pendingResults=useMemo(()=>new Set(readReporterQueue().filter(isResultMutation).filter(item=>item.cupId===cupInfo?.id&&item.state!=="conflict").map(item=>item.matchId)),[cupInfo?.id,pending,matches]);
 const pendingStatuses=useMemo(()=>new Set(readReporterQueue().filter(isStatusMutation).filter(item=>item.cupId===cupInfo?.id&&item.state!=="conflict").map(item=>item.matchId)),[cupInfo?.id,pending,matches]);
 const listedMatches=matches.filter(match=>(includeFinished||lifecycle(match)!=="finished")&&`${match.home_team} ${match.away_team}`.toLocaleLowerCase("sv").includes(matchQuery.toLocaleLowerCase("sv")));
 const focusedMatch=matches.find(match=>match.id===focusMatchId)||null;

 if(!token)return <main className="reporter-page reporter-page--login"><ReporterNavigation cup={null}/><header className="reporter-hero"><p className="kicker">MATCHRAPPORTÖR</p><h1>Matchrapportör</h1><p>Ange koden från arrangören. Du kommer direkt till rätt cup.</p></header><form className="admin-panel reporter-login reporter-login--code-only" onSubmit={login}><div className="reporter-login__fields"><label><span>4-siffrig kod</span><input inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={code} onChange={event=>setCode(event.target.value.replace(/\D/g,"").slice(0,4))} required placeholder="0000" autoComplete="one-time-code" aria-describedby="reporter-code-help"/></label></div>{error&&<p className="reporter-alert reporter-alert--error" role="alert">{error}</p>}<div className="reporter-login__footer"><span id="reporter-code-help">Koden gäller i högst 3 dygn från att arrangören skapar den.</span><button className="is-primary" disabled={busy||code.length!==4}>{busy?"Kontrollerar…":"Öppna matchrapportering"}</button></div></form></main>;
 if(!cupInfo)return <main className="reporter-page"><ReporterNavigation cup={null}/><div className="reporter-network is-syncing" role="status"><span/><strong>Öppnar rapportering…</strong></div></main>;
 return <main className="reporter-page">
  <ReporterNavigation cup={cupInfo}/>
  <div className={`reporter-network is-${online?syncing||pending>0?"syncing":"online":"offline"}`} role="status" aria-live="polite"><span aria-hidden="true"/><strong>{online?syncing?"Synkroniserar":pending>0?"Ändringar väntar":"Sparat":"Offline"}</strong><small>{pending?`${pending} ändring${pending===1?"":"ar"} väntar`:online?"Alla ändringar är synkroniserade":"Inmatningar sparas på mobilen"}</small>{online&&pending>0&&<button type="button" onClick={()=>{window.dispatchEvent(new CustomEvent(SYNC_REQUEST_EVENT));void flushResults()}} disabled={syncing}>Synka nu</button>}</div>
  <header className="reporter-hero reporter-hero--session"><div><p className="kicker">MATCHRAPPORTÖR</p><h1>{cupInfo?.name||"Matchrapportering"}</h1><p>Din behörighet gäller den här cupen. Välj match och starta rapporteringen.</p></div><div className="reporter-hero__actions"><button type="button" onClick={logout}>Logga ut</button></div></header>
  {(error||message)&&<section className={`reporter-alert ${error?"reporter-alert--error":"reporter-alert--success"}`} role={error?"alert":"status"}><strong>{error?"Något gick fel":online?"Status":"Offline"}</strong><span>{error||message}</span></section>}
  {focusedMatch&&<ReporterLiveControl match={focusedMatch} matches={matches} settings={settings} pending={pendingResults.has(focusedMatch.id)||pendingStatuses.has(focusedMatch.id)} onSelect={setFocusMatchId} onScore={changeScore} onStatus={changeStatus}/>} 
  <section className="admin-panel reporter-results"><div className="admin-panel__top"><span>1 / RESULTAT</span><strong>{matches.length} MATCHER</strong></div><div className="reporter-results__head"><div><h2>Rapportera resultat</h2><p>Fyll i båda lagens mål och spara matchen.</p></div><span className="admin-lock">MATCHRAPPORTÖR</span></div><div className="cn-report-filters"><label>Hitta match<input type="search" placeholder="Sök lagnamn" value={matchQuery} onChange={event=>setMatchQuery(event.target.value)}/></label><label className="cn-check"><input type="checkbox" checked={includeFinished} onChange={event=>setIncludeFinished(event.target.checked)}/> Visa slutmarkerade</label></div>{!listedMatches.length&&<div className="cn-notice"><span>{matches.length?"Inga matcher matchar filtret. Prova att visa slutmarkerade matcher.":"Inga matcher kunde visas för din cup."}</span>{!matches.length&&<button type="button" onClick={()=>void load(token).catch(()=>setError("Matcherna kunde inte hämtas. Försök igen."))}>Hämta matcher</button>}</div>}<div className="reporter-match-list">{listedMatches.map(match=><ReporterMatch key={match.id} m={match} busy={busy} pending={pendingResults.has(match.id)} save={save} onOpen={()=>{setFocusMatchId(match.id);document.getElementById("reporter-live-control")?.scrollIntoView({behavior:"smooth",block:"start"})}}/>)}</div></section>
  <ReporterMatchEvents token={token} cupId={cupInfo.id} online={online} queueSignal={pending} enabled={settings} onAuthError={logout}/>
 </main>;
}

function ReporterLiveControl({match,matches,settings,pending,onSelect,onScore,onStatus}:{match:Match;matches:Match[];settings:ReporterSettings;pending:boolean;onSelect:(id:number)=>void;onScore:(match:Match,side:"home"|"away",delta:number)=>void;onStatus:(match:Match,status:MatchLifecycle)=>void}){
 const status=lifecycle(match),home=match.home_score??0,away=match.away_score??0,locked=status==="not_started"||status==="finished";
 const statusLabel=status==="live"?"MATCHEN PÅGÅR":status==="halftime"?"PAUS":status==="finished"?"SLUT":"EJ STARTAD";
 const [now,setNow]=useState(Date.now());
 useEffect(()=>{if(status!=="live")return;const timer=window.setInterval(()=>setNow(Date.now()),1000);return()=>window.clearInterval(timer)},[status]);
 const elapsed=(match.clock_elapsed_seconds||0)+(status==="live"&&match.actual_started_at?Math.max(0,Math.floor((now-Date.parse(match.actual_started_at))/1000)):0);
 const clock=`${String(Math.floor(elapsed/60)).padStart(2,"0")}:${String(elapsed%60).padStart(2,"0")}`;
 return <section id="reporter-live-control" className={`reporter-live is-${status}`} aria-labelledby="reporter-live-title"><div className="reporter-live__top"><div><span>LIVEKONTROLL</span><h2 id="reporter-live-title">Aktiv match</h2></div><strong>{statusLabel}</strong></div><label className="reporter-live__picker"><span>Välj match</span><select value={match.id} onChange={event=>onSelect(Number(event.target.value))}>{matches.map(item=><option key={item.id} value={item.id}>{item.home_team} – {item.away_team}</option>)}</select></label><div className="reporter-live__clock"><span>MATCHKLOCKA</span><strong>{clock}</strong><small>{status==="halftime"?"PAUS":status==="finished"?"SLUT":`HALVLEK ${Math.min(settings.halves,Math.floor(elapsed/(settings.minutes_per_half*60))+1)}/${settings.halves}`}</small></div><div className="reporter-live__scoreboard"><LiveTeam name={match.home_team} score={home} disabled={locked} side="home" onScore={delta=>onScore(match,"home",delta)}/><div className="reporter-live__versus"><span>{match.stage||"MATCH"}</span><b>–</b><small>{pending?"VÄNTAR PÅ SYNK":"SPARAS DIREKT"}</small></div><LiveTeam name={match.away_team} score={away} disabled={locked} side="away" onScore={delta=>onScore(match,"away",delta)}/></div><div className="reporter-live__status-actions">{status==="not_started"&&<button className="is-start" type="button" onClick={()=>onStatus(match,"live")}>Starta match</button>}{status==="live"&&<><button type="button" onClick={()=>onStatus(match,"halftime")}>Paus / halvtid</button><button className="is-finish" type="button" onClick={()=>onStatus(match,"finished")}>Avsluta match</button></>}{status==="halftime"&&<><button className="is-start" type="button" onClick={()=>onStatus(match,"live")}>Fortsätt match</button><button className="is-finish" type="button" onClick={()=>onStatus(match,"finished")}>Avsluta match</button></>}{status==="finished"&&<span>Slutresultat {home}–{away}</span>}</div></section>;
}

function LiveTeam({name,score,disabled,side,onScore}:{name:string;score:number;disabled:boolean;side:"home"|"away";onScore:(delta:number)=>void}){
 return <section className={`reporter-live__team is-${side}`}><span>{side==="home"?"HEMMA":"BORTA"}</span><strong>{name}</strong><b aria-live="polite" aria-atomic="true">{score}</b><div><button type="button" aria-label={`Minska mål för ${name}`} disabled={disabled||score<=0} onClick={()=>onScore(-1)}>−</button><button type="button" aria-label={`Öka mål för ${name}`} disabled={disabled} onClick={()=>onScore(1)}>+</button></div></section>;
}

function ReporterMatch({m,busy,pending,save,onOpen}:{m:Match;busy:boolean;pending:boolean;save:(m:Match,h:string,a:string,hp:string,ap:string)=>void;onOpen:()=>void}){
 const[h,setH]=useState(m.home_score==null?"":String(m.home_score)),[a,setA]=useState(m.away_score==null?"":String(m.away_score));const[hp,setHp]=useState(m.home_penalties==null?"":String(m.home_penalties)),[ap,setAp]=useState(m.away_penalties==null?"":String(m.away_penalties));
 useEffect(()=>{setH(m.home_score==null?"":String(m.home_score));setA(m.away_score==null?"":String(m.away_score));setHp(m.home_penalties==null?"":String(m.home_penalties));setAp(m.away_penalties==null?"":String(m.away_penalties))},[m]);
 const tied=(m.requires_winner??(m.stage!=="Gruppspel"))&&h!==""&&a!==""&&Number(h)===Number(a),saved=m.status==="played",locked=lifecycle(m)==="finished";
 return <article className={`reporter-match${saved?" is-saved":""}${pending?" is-pending":""}`}><div className="reporter-match__meta"><span>{m.scheduled_start?.replace("T"," ")||"Ej schemalagd"}</span><span>{m.stage||"Match"}</span>{pending?<span className="reporter-match__pending">Väntar på nät</span>:saved&&<span className="reporter-match__saved">Sparad</span>}</div><div className="reporter-match__body"><div className="reporter-match__teams"><strong>{m.home_team}</strong><span>mot</span><strong>{m.away_team}</strong></div><div className="reporter-score" aria-label={`${m.home_team} mot ${m.away_team}`}><label><span>{m.home_team}</span><input aria-label={`Mål för ${m.home_team}`} disabled={locked} inputMode="numeric" type="number" min="0" value={h} onChange={event=>setH(event.target.value)}/></label><b>–</b><label><span>{m.away_team}</span><input aria-label={`Mål för ${m.away_team}`} disabled={locked} inputMode="numeric" type="number" min="0" value={a} onChange={event=>setA(event.target.value)}/></label>{tied&&<div className="reporter-penalties"><label>Straffar hemma<input aria-label="Hemmastraffar" disabled={locked} inputMode="numeric" type="number" min="0" value={hp} onChange={event=>setHp(event.target.value)} placeholder="0"/></label><label>Straffar borta<input aria-label="Bortastraffar" disabled={locked} inputMode="numeric" type="number" min="0" value={ap} onChange={event=>setAp(event.target.value)} placeholder="0"/></label></div>}<button type="button" disabled={locked||busy||h===""||a===""||(tied&&(hp===""||ap===""))} onClick={()=>save(m,h,a,hp,ap)}>{locked?"Slutmarkerad":pending?"Uppdatera lokalt":saved?"Uppdatera":"Spara resultat"}</button><button type="button" className="reporter-match__open" onClick={onOpen}>Öppna rapportörsvy</button></div></div></article>;
}
