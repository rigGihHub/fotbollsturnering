"use client";

import {FormEvent,useCallback,useEffect,useMemo,useRef,useState} from "react";
import dynamic from "next/dynamic";
import {ReporterApiError,reporterCall as call} from "../lib/reporter-api";
import {ReporterMatch as Match,MatchLifecycle,reporterMatchLifecycle,reporterElapsedSeconds,reporterStatusProjection,overlayReporterMatches} from "../lib/reporter-match";
export {reporterMatchLifecycle} from "../lib/reporter-match";
import {reporterSessionDeadline} from "../lib/reporter-session";
import {QUEUE_EVENT,SYNC_REQUEST_EVENT,appendReporterMutation,completeReporterResultMutation,discardReporterConflicts,isNetworkError,nextReporterMutationTime,isResultMutation,isResultOrStatusMutation,isStatusMutation,readReporterCache,readReporterQueue,removeReporterMutation,reporterQueueSummary,retryReporterConflicts,updateReporterMutation,upsertReporterMutation,writeReporterCache} from "../lib/reporter-offline";
import ReporterNavigation from "./reporter-navigation";

const ReporterMatchEvents=dynamic(()=>import("./reporter-match-events"));

const KEY="cupnavi_reporter_session_v1",SESSION_CACHE="session";
// Rollgräns: Cupinställningar är inte åtkomliga här; rapportören kan bara arbeta med matchdata.
// Målskyttar, assist och kort renderas separat och följer cupens aktiverade rapporteringsfält.
type Cup={id:number;name:string;public_slug?:string|null};
type ReporterSettings={scorers:boolean;assists:boolean;cards:boolean;fairness:boolean;minutes_per_half:number;halves:number};
type CachedSession={cup:Cup;matches:Match[];settings?:ReporterSettings};
const DEFAULT_SETTINGS:ReporterSettings={scorers:true,assists:true,cards:true,fairness:false,minutes_per_half:20,halves:2};
const lifecycle=reporterMatchLifecycle;
const isAuthFailure=(error:unknown)=>error instanceof ReporterApiError?error.status===401||error.status===403:/(401|session|inloggning krävs|ogiltig|gått ut|authentication)/i.test(error instanceof Error?error.message:String(error));

export default function ReporterClient(){
 const[code,setCode]=useState("");
 const[matchQuery,setMatchQuery]=useState("");
 const[includeFinished,setIncludeFinished]=useState(false);
 const[token,setToken]=useState<string|null>(null),[cupInfo,setCupInfo]=useState<Cup|null>(null),[matches,setMatches]=useState<Match[]>([]),[settings,setSettings]=useState<ReporterSettings>(DEFAULT_SETTINGS);
 const[busy,setBusy]=useState(false),[syncing,setSyncing]=useState(false),[online,setOnline]=useState(true),[pending,setPending]=useState(0),[conflicts,setConflicts]=useState(0);
 const[focusMatchId,setFocusMatchId]=useState<number|null>(null);
 const[error,setError]=useState(""),[message,setMessage]=useState("");
 const settingsRef=useRef<ReporterSettings>(DEFAULT_SETTINGS);
 const syncingRef=useRef(false),reportingRequestRef=useRef(0),tokenRef=useRef<string|null>(null);
 const logout=useCallback(()=>{localStorage.removeItem(KEY);tokenRef.current=null;setToken(null);setCupInfo(null);setMatches([]);setMessage("");setError("")},[]);
 const remember=useCallback((nextCup:Cup,nextMatches:Match[],nextSettings=settingsRef.current)=>writeReporterCache<CachedSession>(SESSION_CACHE,{cup:nextCup,matches:nextMatches,settings:nextSettings}),[]);
 const applyReporting=useCallback((nextCup:Cup,reporting:{matches:Match[];settings?:ReporterSettings})=>{
  const next=overlayReporterMatches(reporting.matches||[],nextCup.id),nextSettings={...DEFAULT_SETTINGS,...(reporting.settings||{})};settingsRef.current=nextSettings;setCupInfo(nextCup);setMatches(next);setSettings(nextSettings);remember(nextCup,next,nextSettings);
 },[remember]);
 const load=useCallback(async(sessionToken:string)=>{
  const request=++reportingRequestRef.current;
  const reporting=await call<{cup:Cup;matches:Match[];settings?:ReporterSettings}>("/api/reporter/reporting",sessionToken);
  if(tokenRef.current!==sessionToken||request!==reportingRequestRef.current)return;
  const queryCup=new URLSearchParams(window.location.search).get("cup");
  if(queryCup&&queryCup!==String(reporting.cup.id)&&queryCup!==reporting.cup.public_slug){logout();setError("Koden gäller en annan cup. Ange en rapportörskod för den här cupen.");return}
  if(request===reportingRequestRef.current&&tokenRef.current===sessionToken)applyReporting(reporting.cup,reporting);
 },[applyReporting,logout]);
 useEffect(()=>{
  if(!matches.length){setFocusMatchId(null);return}
  let savedId:number|null=null;try{savedId=Number(localStorage.getItem(`cupnavi_reporter_focus_${cupInfo?.id}`))||null}catch{}
  setFocusMatchId(current=>current&&matches.some(match=>match.id===current)?current:savedId&&matches.some(match=>match.id===savedId)?savedId:(matches.find(match=>["live","halftime"].includes(lifecycle(match)))||matches.find(match=>lifecycle(match)!=="finished")||matches[0]).id);
 },[cupInfo?.id,matches]);
 useEffect(()=>{if(cupInfo&&focusMatchId)try{localStorage.setItem(`cupnavi_reporter_focus_${cupInfo.id}`,String(focusMatchId))}catch{}},[cupInfo,focusMatchId]);

 useEffect(()=>{
  const refresh=()=>{const summary=reporterQueueSummary(cupInfo?.id);setOnline(navigator.onLine);setPending(summary.pending);setConflicts(summary.conflicts)};refresh();
  window.addEventListener("online",refresh);window.addEventListener("offline",refresh);window.addEventListener(QUEUE_EVENT,refresh);
  return()=>{window.removeEventListener("online",refresh);window.removeEventListener("offline",refresh);window.removeEventListener(QUEUE_EVENT,refresh)};
 },[cupInfo?.id]);
 useEffect(()=>{
  const queryCup=new URLSearchParams(window.location.search).get("cup");
  const stored=localStorage.getItem(KEY);if(!stored)return;tokenRef.current=stored;setToken(stored);
  const cached=readReporterCache<CachedSession>(SESSION_CACHE),cacheMatchesLink=!queryCup||queryCup===cached?.cup.public_slug||queryCup===String(cached?.cup.id);
  if(cached&&cacheMatchesLink){const cachedSettings={...DEFAULT_SETTINGS,...(cached.settings||{})};settingsRef.current=cachedSettings;setCupInfo(cached.cup);setMatches(overlayReporterMatches(cached.matches,cached.cup.id));setSettings(cachedSettings)}
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
  if(!token||!cupInfo||!navigator.onLine||syncingRef.current)return;
  const nextMutation=()=>readReporterQueue().filter(isResultOrStatusMutation).filter(item=>item.cupId===cupInfo.id&&item.state!=="conflict").sort((a,b)=>a.createdAt-b.createdAt)[0];
  if(!nextMutation())return;
  syncingRef.current=true;setSyncing(true);
  try{
   const reporting=await call<{matches:Match[];settings?:ReporterSettings}>("/api/reporter/reporting",token);let serverMatches=reporting.matches||[];
   for(let count=0;count<100&&tokenRef.current===token;count++){
    const mutation=nextMutation();if(!mutation)break;
    const current=serverMatches.find(item=>item.id===mutation.matchId);
    const blocked=readReporterQueue().some(item=>item.cupId===cupInfo.id&&item.matchId===mutation.matchId&&item.state==="conflict");
    if(!current||blocked){updateReporterMutation(mutation.id,{state:"conflict"});continue}
    if(isStatusMutation(mutation)&&mutation.payload.status==="finished"&&readReporterQueue().some(item=>item.cupId===cupInfo.id&&item.matchId===mutation.matchId&&item.kind==="event"&&item.state!=="conflict"))break;
    try{
     if(isResultMutation(mutation)){
      const desired=current.home_score===mutation.payload.home_score&&current.away_score===mutation.payload.away_score&&(current.home_penalties??null)===mutation.payload.home_penalties&&(current.away_penalties??null)===mutation.payload.away_penalties;
      if(desired){completeReporterResultMutation(mutation);continue}
      const unchanged=current.home_score===mutation.payload.expected_home_score&&current.away_score===mutation.payload.expected_away_score&&(current.home_penalties??null)===mutation.payload.expected_home_penalties&&(current.away_penalties??null)===mutation.payload.expected_away_penalties;
      if(!unchanged)throw new ReporterApiError("En lokal ändring krockar med ett nyare serverresultat och har inte skrivits över.",409);
      const saved=await call<Partial<Match>>(`/api/reporter/reporting/matches/${mutation.matchId}`,token,{method:"PUT",body:JSON.stringify(mutation.payload)});
      completeReporterResultMutation(mutation);
      serverMatches=serverMatches.map(item=>item.id===mutation.matchId?{...item,...saved}:item);
     }else{
      const currentStatus=lifecycle(current);
      if(currentStatus===mutation.payload.status){removeReporterMutation(mutation.id);continue}
      if(currentStatus!==mutation.payload.expected_status)throw new ReporterApiError("En statusändring krockar med en nyare matchstatus och har stoppats.",409);
      const saved=await call<Partial<Match>>(`/api/reporter/reporting/matches/${mutation.matchId}/status`,token,{method:"PUT",body:JSON.stringify(mutation.payload)});
      removeReporterMutation(mutation.id);
      serverMatches=serverMatches.map(item=>item.id===mutation.matchId?{...item,...saved,match_status:mutation.payload.status,status:mutation.payload.status==="finished"?"played":mutation.payload.status}:item);
     }
    }catch(reason){
     if(isNetworkError(reason)||isAuthFailure(reason))throw reason;
     updateReporterMutation(mutation.id,{state:"conflict"});setError(reason instanceof Error?reason.message:"Ändringen behöver kontrolleras.");
    }
   }
   await load(token);const summary=reporterQueueSummary(cupInfo.id);setMessage(summary.conflicts?"En eller flera ändringar behöver kontrolleras.":summary.pending?"Vissa ändringar väntar fortfarande. Kontrollera meddelandet ovan.":"Alla ändringar är sparade på servern.");
  }catch(reason){if(isAuthFailure(reason)){logout();setError("Koden har gått ut eller dragits in. Be arrangören om en ny kod. Lokala ändringar finns kvar.")}else if(isNetworkError(reason)){setMessage("Anslutningen är osäker. Ändringarna finns kvar lokalt och försöker skickas igen.")}else setError(reason instanceof Error?reason.message:"Offlinekön kunde inte synkroniseras.")}
  finally{const summary=reporterQueueSummary(cupInfo.id);syncingRef.current=false;setSyncing(false);setPending(summary.pending);setConflicts(summary.conflicts)}
 },[cupInfo,load,logout,token]);
 useEffect(()=>{if(!online||pending===0)return;const retry=window.setTimeout(()=>void flushResults(),500);const interval=window.setInterval(()=>void flushResults(),5000);return()=>{window.clearTimeout(retry);window.clearInterval(interval)}},[online,pending,flushResults]);
 useEffect(()=>{const refresh=()=>{if(!token||!navigator.onLine)return;if(reporterQueueSummary(cupInfo?.id).pending)void flushResults();else void load(token).catch(reason=>{if(isAuthFailure(reason))logout()})};window.addEventListener("focus",refresh);window.addEventListener("online",refresh);const interval=window.setInterval(refresh,15000);return()=>{window.removeEventListener("focus",refresh);window.removeEventListener("online",refresh);window.clearInterval(interval)}},[cupInfo?.id,flushResults,load,logout,token]);

 async function login(event:FormEvent){event.preventDefault();setBusy(true);setError("");try{void navigator.storage?.persist?.().catch(()=>false);const result=await call<{token:string;cup:Cup;matches:Match[];settings?:ReporterSettings}>("/api/reporter/session",null,{method:"POST",body:JSON.stringify({code,cup:new URLSearchParams(window.location.search).get("cup")||undefined,include_reporting:true})});localStorage.setItem(KEY,result.token);tokenRef.current=result.token;setToken(result.token);setCode("");applyReporting(result.cup,result)}catch(reason){setError(reason instanceof Error?reason.message:"Inloggningen misslyckades.")}finally{setBusy(false)}}
 function optimisticResult(match:Match,payload:{home_score:number;away_score:number;home_penalties:number|null;away_penalties:number|null}){
  setMatches(current=>{const next=current.map(item=>item.id===match.id?{...item,...payload,status:"played"}:item);if(cupInfo)remember(cupInfo,next);return next});
 }
 function save(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string,goal?:{side:"home"|"away";minute:number}):boolean{
  if(!token||!cupInfo)return false;
  if([home,away,homePenalties,awayPenalties].filter(value=>value!=="").some(value=>!Number.isInteger(Number(value))||Number(value)<0)){setError("Mål och straffar måste vara hela tal från 0 och uppåt.");return false}
  const payload={home_score:Number(home),away_score:Number(away),home_penalties:homePenalties===""?null:Number(homePenalties),away_penalties:awayPenalties===""?null:Number(awayPenalties),expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null,goal_minutes_home:goal?.side==="home"?[goal.minute]:[],goal_minutes_away:goal?.side==="away"?[goal.minute]:[]};
  const mutation={id:`result-${cupInfo.id}-${match.id}`,kind:"result" as const,cupId:cupInfo.id,matchId:match.id,createdAt:nextReporterMutationTime(),state:"queued" as const,payload};setError("");setMessage("");
  try{upsertReporterMutation(mutation)}catch(reason){setError(reason instanceof Error?reason.message:"Ändringen kunde inte sparas lokalt.");return false}
  optimisticResult(match,payload);setMessage(navigator.onLine?"Registrerat – synkroniserar med servern.":"Sparat lokalt. Resultatet skickas när nätet är tillbaka och stäms av mot servern.");return true;
 }
 function changeScore(match:Match,side:"home"|"away",delta:number,chosenMinute?:number){
  if(delta>0&&chosenMinute!==undefined&&(!Number.isInteger(chosenMinute)||chosenMinute<1||chosenMinute>300)){setError("Ange en målminut mellan 1 och 300.");return}
  const home=Math.max(0,(match.home_score??0)+(side==="home"?delta:0)),away=Math.max(0,(match.away_score??0)+(side==="away"?delta:0));
  if(home===(match.home_score??0)&&away===(match.away_score??0))return;
  const seconds=reporterElapsedSeconds(match);
  const goal=delta>0&&Number.isFinite(seconds)&&["live","halftime"].includes(lifecycle(match))?{side,minute:chosenMinute??Math.max(1,Math.min(300,Math.ceil(seconds/60)))}:undefined;
  if(save(match,String(home),String(away),match.home_penalties==null?"":String(match.home_penalties),match.away_penalties==null?"":String(match.away_penalties),goal)&&delta>0&&typeof navigator.vibrate==="function")navigator.vibrate(25);
 }
 function changeStatus(match:Match,next:MatchLifecycle){
  if(!cupInfo)return;const current=lifecycle(match);
  if(current==="finished"&&!window.confirm(`${next==="live"?"Återuppta":"Öppna för rättning"} ${match.home_team} – ${match.away_team}? Resultatet och matchklockan behålls.`))return;
  if(next==="finished"){
   if((match.requires_winner??(match.stage!=="Gruppspel"))&&(match.home_score??0)===(match.away_score??0)&&match.home_penalties==null){setError("En oavgjord slutspelsmatch måste avgöras innan den avslutas.");return}
   if(!window.confirm(`Avsluta ${match.home_team} – ${match.away_team}?`))return;
   if((match.home_score==null||match.away_score==null)&&!save(match,String(match.home_score??0),String(match.away_score??0),"",""))return;
  }
  const mutation={id:`status-${cupInfo.id}-${match.id}-${Date.now()}-${next}`,kind:"status" as const,cupId:cupInfo.id,matchId:match.id,createdAt:nextReporterMutationTime(),state:"queued" as const,payload:{status:next,expected_status:current}};
  try{appendReporterMutation(mutation)}catch(reason){setError(reason instanceof Error?reason.message:"Ändringen kunde inte sparas lokalt.");return}
  setMatches(rows=>{const updated=rows.map(item=>item.id===match.id?reporterStatusProjection(item,next,mutation.createdAt):item);remember(cupInfo,updated);return updated});setError("");setMessage(navigator.onLine?"Matchstatus uppdaterad – synkroniserar.":"Matchstatus sparad lokalt och skickas när nätet är tillbaka.");
 }
 const pendingResults=useMemo(()=>new Set(readReporterQueue().filter(isResultMutation).filter(item=>item.cupId===cupInfo?.id&&item.state!=="conflict").map(item=>item.matchId)),[cupInfo?.id,pending,matches]);
 const pendingStatuses=useMemo(()=>new Set(readReporterQueue().filter(isStatusMutation).filter(item=>item.cupId===cupInfo?.id&&item.state!=="conflict").map(item=>item.matchId)),[cupInfo?.id,pending,matches]);
 const listedMatches=matches.filter(match=>(includeFinished||lifecycle(match)!=="finished"||pendingResults.has(match.id))&&`${match.home_team} ${match.away_team}`.toLocaleLowerCase("sv").includes(matchQuery.toLocaleLowerCase("sv")));
 const focusedMatch=matches.find(match=>match.id===focusMatchId)||null;
 const retryConflicts=()=>{if(!cupInfo)return;retryReporterConflicts(cupInfo.id);setError("");setMessage("Kontrollerar ändringarna mot servern igen.");window.dispatchEvent(new CustomEvent(SYNC_REQUEST_EVENT));void flushResults()};
 const useServerVersion=()=>{if(!cupInfo||!token||!window.confirm("Ta bort lokala konfliktändringar och hämta serverns aktuella version?"))return;discardReporterConflicts(cupInfo.id);window.location.reload()};

 if(!token)return <main className="reporter-page reporter-page--login"><ReporterNavigation cup={null}/><header className="reporter-hero"><p className="kicker">MATCHRAPPORTÖR</p><h1>Matchrapportör</h1><p>Ange koden från arrangören. Du kommer direkt till rätt cup.</p></header><form className="admin-panel reporter-login reporter-login--code-only" onSubmit={login}><div className="reporter-login__fields"><label><span>4-siffrig kod</span><input inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={code} onChange={event=>setCode(event.target.value.replace(/\D/g,"").slice(0,4))} required placeholder="0000" autoComplete="one-time-code" aria-describedby="reporter-code-help"/></label></div>{error&&<p className="reporter-alert reporter-alert--error" role="alert">{error}</p>}<div className="reporter-login__footer"><span id="reporter-code-help">Koden gäller i högst 3 dygn från att arrangören skapar den.</span><button className="is-primary" disabled={busy||code.length!==4}>{busy?"Kontrollerar…":"Öppna matchrapportering"}</button></div></form></main>;
 if(!cupInfo)return <main className="reporter-page"><ReporterNavigation cup={null}/><div className="reporter-network is-syncing" role="status"><span/><strong>Öppnar rapportering…</strong></div></main>;
 return <main className="reporter-page">
  <ReporterNavigation cup={cupInfo}/>
  <div className={`reporter-network is-${conflicts>0?"conflict":online?syncing||pending>0?"syncing":"online":"offline"}`} role="status" aria-live="polite"><span aria-hidden="true"/><strong>{conflicts>0?"Åtgärd krävs":online?syncing?"Synkroniserar":pending>0?"Ändringar väntar":"Sparat":"Offline"}</strong><small>{conflicts>0?`${conflicts} ändring${conflicts===1?"":"ar"} krockar med servern`:pending?`${pending} ändring${pending===1?"":"ar"} väntar`:online?"Alla ändringar är synkroniserade":"Inmatningar sparas på den här enheten"}</small>{pending>0&&<small>Behåll den här enhetens webbläsardata tills synkroniseringen är klar. Osynkade ändringar finns bara här.</small>}{conflicts>0&&online?<span className="reporter-network__actions"><button type="button" onClick={retryConflicts} disabled={syncing}>Kontrollera igen</button><button type="button" onClick={useServerVersion} disabled={syncing}>Använd serverns version</button></span>:online&&pending>0&&<button type="button" onClick={()=>{window.dispatchEvent(new CustomEvent(SYNC_REQUEST_EVENT));void flushResults()}} disabled={syncing}>Synka nu</button>}</div>
  <header className="reporter-hero reporter-hero--session"><div><p className="kicker">MATCHRAPPORTÖR</p><h1>{cupInfo?.name||"Matchrapportering"}</h1><p>Din behörighet gäller den här cupen. Välj match och starta rapporteringen.</p></div><div className="reporter-hero__actions"><button type="button" onClick={logout}>Logga ut</button></div></header>
  {(error||message)&&<section className={`reporter-alert ${error?"reporter-alert--error":"reporter-alert--success"}`} role={error?"alert":"status"}><strong>{error?"Något gick fel":online?"Status":"Offline"}</strong><span>{error||message}</span></section>}
  {focusedMatch&&<ReporterLiveControl match={focusedMatch} matches={matches} settings={settings} pending={pendingResults.has(focusedMatch.id)||pendingStatuses.has(focusedMatch.id)} onSelect={setFocusMatchId} onScore={changeScore} onStatus={changeStatus}/>} 
  <section className="admin-panel reporter-results"><div className="admin-panel__top"><span>1 / RESULTAT</span><strong>{matches.length} MATCHER</strong></div><div className="reporter-results__head"><div><h2>Rapportera resultat</h2><p>Fyll i båda lagens mål och spara matchen.</p></div><span className="admin-lock">MATCHRAPPORTÖR</span></div><div className="cn-report-filters"><label>Hitta match<input type="search" placeholder="Sök lagnamn" value={matchQuery} onChange={event=>setMatchQuery(event.target.value)}/></label><label className="cn-check"><input type="checkbox" checked={includeFinished} onChange={event=>setIncludeFinished(event.target.checked)}/> Visa slutmarkerade</label></div>{!listedMatches.length&&<div className="cn-notice"><span>{matches.length?"Inga matcher matchar filtret. Prova att visa slutmarkerade matcher.":"Inga matcher kunde visas för din cup."}</span>{!matches.length&&<button type="button" onClick={()=>void load(token).catch(()=>setError("Matcherna kunde inte hämtas. Försök igen."))}>Hämta matcher</button>}</div>}<div className="reporter-match-list">{listedMatches.map(match=><ReporterMatch key={match.id} m={match} busy={busy} pending={pendingResults.has(match.id)} save={save} onOpen={()=>{setFocusMatchId(match.id);document.getElementById("reporter-live-control")?.scrollIntoView({behavior:"smooth",block:"start"})}}/>)}</div></section>
  <ReporterMatchEvents key={cupInfo.id} selectedMatchId={focusMatchId} matchStatus={focusedMatch?lifecycle(focusedMatch):"not_started"} reportingSignal={matches} token={token} cupId={cupInfo.id} online={online} queueSignal={pending} enabled={settings} onAuthError={logout}/>
 </main>;
}

function ReporterLiveControl({match,matches,settings,pending,onSelect,onScore,onStatus}:{match:Match;matches:Match[];settings:ReporterSettings;pending:boolean;onSelect:(id:number)=>void;onScore:(match:Match,side:"home"|"away",delta:number,minute?:number)=>void;onStatus:(match:Match,status:MatchLifecycle)=>void}){
 const status=lifecycle(match),home=match.home_score??0,away=match.away_score??0,locked=status==="not_started"||status==="finished";
 const statusLabel=status==="live"?"MATCHEN PÅGÅR":status==="halftime"?"PAUS":status==="finished"?"SLUT":"EJ STARTAD";
 const [now,setNow]=useState(Date.now());
 const [goalMinute,setGoalMinute]=useState("");
 useEffect(()=>setGoalMinute(""),[match.id]);
 useEffect(()=>{if(status!=="live")return;const timer=window.setInterval(()=>setNow(Date.now()),1000);return()=>window.clearInterval(timer)},[status]);
 const elapsed=reporterElapsedSeconds(match,now);
 const clock=`${String(Math.floor(elapsed/60)).padStart(2,"0")}:${String(elapsed%60).padStart(2,"0")}`;
 const selectedMinute=goalMinute?Number(goalMinute):undefined;
 return <section id="reporter-live-control" className={`reporter-live is-${status}`} aria-labelledby="reporter-live-title"><div className="reporter-live__top"><div><span>LIVEKONTROLL</span><h2 id="reporter-live-title">Aktiv match</h2></div><strong>{statusLabel}</strong></div><label className="reporter-live__picker"><span>Välj match</span><select value={match.id} onChange={event=>onSelect(Number(event.target.value))}>{matches.map(item=><option key={item.id} value={item.id}>{item.home_team} – {item.away_team}</option>)}</select></label><div className="reporter-live__clock"><span>MATCHKLOCKA</span><strong>{clock}</strong><small>{status==="halftime"?"PAUS":status==="finished"?"SLUT":`HALVLEK ${Math.min(settings.halves,Math.floor(elapsed/(settings.minutes_per_half*60))+1)}/${settings.halves}`}</small></div>{!locked&&<label className="reporter-live__goal-minute">Målminut för nästa mål <input type="number" inputMode="numeric" min="1" max="300" placeholder={String(Math.max(1,Math.min(300,Math.ceil(elapsed/60))))} value={goalMinute} onChange={event=>setGoalMinute(event.target.value)} /> <small>Lämna tomt för matchklockans minut.</small></label>}<div className="reporter-live__scoreboard"><LiveTeam name={match.home_team} score={home} disabled={locked} side="home" onScore={delta=>onScore(match,"home",delta,selectedMinute)}/><div className="reporter-live__versus"><span>{match.stage||"MATCH"}</span><b>–</b><small>{pending?"VÄNTAR PÅ SYNK":"SPARAS DIREKT"}</small></div><LiveTeam name={match.away_team} score={away} disabled={locked} side="away" onScore={delta=>onScore(match,"away",delta,selectedMinute)}/></div><div className="reporter-live__status-actions">{status==="not_started"&&<button className="is-start" type="button" onClick={()=>onStatus(match,"live")}>Starta match</button>}{status==="live"&&<><button type="button" onClick={()=>onStatus(match,"halftime")}>Paus / halvtid</button><button className="is-finish" type="button" onClick={()=>onStatus(match,"finished")}>Avsluta match</button></>}{status==="halftime"&&<><button className="is-start" type="button" onClick={()=>onStatus(match,"live")}>Fortsätt match</button><button className="is-finish" type="button" onClick={()=>onStatus(match,"finished")}>Avsluta match</button></>}{status==="finished"&&<><span>Slutresultat {home}–{away}</span><button type="button" onClick={()=>onStatus(match,"halftime")}>Rätta slutresultat</button><button className="is-start" type="button" onClick={()=>onStatus(match,"live")}>Återuppta match</button></>}</div></section>;
}

function LiveTeam({name,score,disabled,side,onScore}:{name:string;score:number;disabled:boolean;side:"home"|"away";onScore:(delta:number)=>void}){
 return <section className={`reporter-live__team is-${side}`}><span>{side==="home"?"HEMMA":"BORTA"}</span><strong>{name}</strong><b aria-live="polite" aria-atomic="true">{score}</b><div><button type="button" aria-label={`Minska mål för ${name}`} disabled={disabled||score<=0} onClick={()=>onScore(-1)}>−</button><button type="button" aria-label={`Öka mål för ${name}`} disabled={disabled} onClick={()=>onScore(1)}>+</button></div></section>;
}

function ReporterMatch({m,busy,pending,save,onOpen}:{m:Match;busy:boolean;pending:boolean;save:(m:Match,h:string,a:string,hp:string,ap:string)=>void;onOpen:()=>void}){
 const[h,setH]=useState(m.home_score==null?"":String(m.home_score)),[a,setA]=useState(m.away_score==null?"":String(m.away_score));const[hp,setHp]=useState(m.home_penalties==null?"":String(m.home_penalties)),[ap,setAp]=useState(m.away_penalties==null?"":String(m.away_penalties));
 useEffect(()=>{setH(m.home_score==null?"":String(m.home_score));setA(m.away_score==null?"":String(m.away_score));setHp(m.home_penalties==null?"":String(m.home_penalties));setAp(m.away_penalties==null?"":String(m.away_penalties))},[m.home_score,m.away_score,m.home_penalties,m.away_penalties]);
 const tied=(m.requires_winner??(m.stage!=="Gruppspel"))&&h!==""&&a!==""&&Number(h)===Number(a),saved=m.status==="played",locked=lifecycle(m)==="finished";
 return <article className={`reporter-match${saved?" is-saved":""}${pending?" is-pending":""}`}><div className="reporter-match__meta"><span>{m.scheduled_start?.replace("T"," ")||"Ej schemalagd"}</span><span>{m.stage||"Match"}</span>{pending?<span className="reporter-match__pending">Väntar på nät</span>:saved&&<span className="reporter-match__saved">Sparad</span>}</div><div className="reporter-match__body"><div className="reporter-match__teams"><strong>{m.home_team}</strong><span>mot</span><strong>{m.away_team}</strong></div><div className="reporter-score" aria-label={`${m.home_team} mot ${m.away_team}`}><label><span>{m.home_team}</span><input aria-label={`Mål för ${m.home_team}`} disabled={locked} inputMode="numeric" type="number" min="0" value={h} onChange={event=>setH(event.target.value)}/></label><b>–</b><label><span>{m.away_team}</span><input aria-label={`Mål för ${m.away_team}`} disabled={locked} inputMode="numeric" type="number" min="0" value={a} onChange={event=>setA(event.target.value)}/></label>{tied&&<div className="reporter-penalties"><label>Straffar hemma<input aria-label="Hemmastraffar" disabled={locked} inputMode="numeric" type="number" min="0" value={hp} onChange={event=>setHp(event.target.value)} placeholder="0"/></label><label>Straffar borta<input aria-label="Bortastraffar" disabled={locked} inputMode="numeric" type="number" min="0" value={ap} onChange={event=>setAp(event.target.value)} placeholder="0"/></label></div>}<button type="button" disabled={locked||busy||h===""||a===""||(tied&&(hp===""||ap===""))} onClick={()=>save(m,h,a,hp,ap)}>{locked?"Slutmarkerad":pending?"Uppdatera lokalt":saved?"Uppdatera":"Spara resultat"}</button><button type="button" className="reporter-match__open" onClick={onOpen}>Öppna rapportörsvy</button></div></div></article>;
}
