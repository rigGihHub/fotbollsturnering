"use client";

import {FormEvent,useCallback,useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";
import {QUEUE_EVENT,isNetworkError,isResultMutation,pendingReporterCount,readReporterCache,readReporterQueue,removeReporterMutation,updateReporterMutation,upsertReporterMutation,writeReporterCache} from "../lib/reporter-offline";
import ReporterMatchEvents from "./reporter-match-events";

const API=CLIENT_API_BASE,KEY="cupnavi_reporter_session_v1",SESSION_CACHE="session";
// Rollgräns: Cupinställningar är inte åtkomliga här; rapportören kan bara arbeta med matchdata.
type Cup={id:number;name:string;public_slug?:string|null};
type Match={id:number;stage?:string|null;home_team:string;away_team:string;home_score:number|null;away_score:number|null;home_penalties?:number|null;away_penalties?:number|null;status:string;scheduled_start?:string|null};
type CachedSession={cup:Cup;matches:Match[]};

async function call<T>(path:string,token?:string|null,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);if(token)headers.set("Authorization",`Bearer ${token}`);if(init.body)headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);return payload as T;
}

export default function ReporterClient(){
 const[cup,setCup]=useState(""),[linkedCup,setLinkedCup]=useState(false),[code,setCode]=useState("");
 const[token,setToken]=useState<string|null>(null),[cupInfo,setCupInfo]=useState<Cup|null>(null),[matches,setMatches]=useState<Match[]>([]);
 const[busy,setBusy]=useState(false),[syncing,setSyncing]=useState(false),[online,setOnline]=useState(true),[pending,setPending]=useState(0);
 const[error,setError]=useState(""),[message,setMessage]=useState("");
 const logout=useCallback(()=>{localStorage.removeItem(KEY);setToken(null);setCupInfo(null);setMatches([]);setMessage("");setError("")},[]);
 const remember=useCallback((nextCup:Cup,nextMatches:Match[])=>writeReporterCache<CachedSession>(SESSION_CACHE,{cup:nextCup,matches:nextMatches}),[]);
 const load=useCallback(async(sessionToken:string)=>{
  const[session,reporting]=await Promise.all([call<{cup:Cup}>("/api/reporter/session",sessionToken),call<{matches:Match[]}>("/api/reporter/reporting",sessionToken)]);
  const next=reporting.matches||[];setCupInfo(session.cup);setMatches(next);remember(session.cup,next);
 },[remember]);

 useEffect(()=>{
  const refresh=()=>{setOnline(navigator.onLine);setPending(pendingReporterCount(cupInfo?.id))};refresh();
  window.addEventListener("online",refresh);window.addEventListener("offline",refresh);window.addEventListener(QUEUE_EVENT,refresh);
  return()=>{window.removeEventListener("online",refresh);window.removeEventListener("offline",refresh);window.removeEventListener(QUEUE_EVENT,refresh)};
 },[cupInfo?.id]);
 useEffect(()=>{
  const queryCup=new URLSearchParams(window.location.search).get("cup");if(queryCup){setCup(queryCup);setLinkedCup(true)}
  const stored=localStorage.getItem(KEY);if(!stored)return;setToken(stored);
  void load(stored).catch(()=>{const cached=readReporterCache<CachedSession>(SESSION_CACHE);const cacheMatchesLink=!queryCup||queryCup===cached?.cup.public_slug||queryCup===String(cached?.cup.id);if(!navigator.onLine&&cached&&cacheMatchesLink){setCupInfo(cached.cup);setMatches(cached.matches);setMessage("Offline: senast hämtade matcher visas.")}else logout()});
 },[load,logout]);

 const flushResults=useCallback(async()=>{
  if(!token||!cupInfo||!navigator.onLine||syncing)return;const queued=readReporterQueue().filter(isResultMutation).filter(item=>item.cupId===cupInfo.id);if(!queued.length)return;
  setSyncing(true);
  try{
   const reporting=await call<{matches:Match[]}>("/api/reporter/reporting",token);let serverMatches=reporting.matches||[];
   for(const mutation of queued){
    const current=serverMatches.find(item=>item.id===mutation.matchId);if(!current){updateReporterMutation(mutation.id,{state:"conflict"});continue}
    const desired=current.home_score===mutation.payload.home_score&&current.away_score===mutation.payload.away_score&&(current.home_penalties??null)===mutation.payload.home_penalties&&(current.away_penalties??null)===mutation.payload.away_penalties;
    if(desired){removeReporterMutation(mutation.id);continue}
    const unchanged=current.home_score===mutation.payload.expected_home_score&&current.away_score===mutation.payload.expected_away_score&&(current.home_penalties??null)===mutation.payload.expected_home_penalties&&(current.away_penalties??null)===mutation.payload.expected_away_penalties;
    if(!unchanged){updateReporterMutation(mutation.id,{state:"conflict"});setError("En offlineändring krockar med ett nyare serverresultat och har inte skrivits över.");continue}
    await call(`/api/reporter/reporting/matches/${mutation.matchId}`,token,{method:"PUT",body:JSON.stringify(mutation.payload)});removeReporterMutation(mutation.id);
    serverMatches=serverMatches.map(item=>item.id===mutation.matchId?{...item,home_score:mutation.payload.home_score,away_score:mutation.payload.away_score,home_penalties:mutation.payload.home_penalties,away_penalties:mutation.payload.away_penalties,status:"played"}:item);
   }
   await load(token);setMessage("Offlinekö synkroniserad med servern.");
  }catch(reason){if(!isNetworkError(reason))setError(reason instanceof Error?reason.message:"Offlinekön kunde inte synkroniseras.")}
  finally{setSyncing(false);setPending(pendingReporterCount(cupInfo.id))}
 },[cupInfo,load,syncing,token]);
 useEffect(()=>{if(!online||pending===0)return;const retry=window.setTimeout(()=>void flushResults(),1500);return()=>window.clearTimeout(retry)},[online,pending,flushResults]);

 async function login(event:FormEvent){event.preventDefault();setBusy(true);setError("");try{const result=await call<{token:string;cup:Cup}>("/api/reporter/session",null,{method:"POST",body:JSON.stringify({cup,code})});localStorage.setItem(KEY,result.token);setToken(result.token);setCupInfo(result.cup);setCode("");await load(result.token)}catch(reason){setError(reason instanceof Error?reason.message:"Inloggningen misslyckades.")}finally{setBusy(false)}}
 function optimisticResult(match:Match,payload:{home_score:number;away_score:number;home_penalties:number|null;away_penalties:number|null}){
  setMatches(current=>{const next=current.map(item=>item.id===match.id?{...item,...payload,status:"played"}:item);if(cupInfo)remember(cupInfo,next);return next});
 }
 async function save(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string){
  if(!token||!cupInfo)return;const payload={home_score:Number(home),away_score:Number(away),home_penalties:homePenalties===""?null:Number(homePenalties),away_penalties:awayPenalties===""?null:Number(awayPenalties),expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null};
  const mutation={id:`result-${cupInfo.id}-${match.id}`,kind:"result" as const,cupId:cupInfo.id,matchId:match.id,createdAt:Date.now(),state:"queued" as const,payload};setError("");setMessage("");
  if(!navigator.onLine){upsertReporterMutation(mutation);optimisticResult(match,payload);setMessage("Sparat lokalt. Resultatet skickas när nätet är tillbaka.");return}
  setBusy(true);try{await call(`/api/reporter/reporting/matches/${match.id}`,token,{method:"PUT",body:JSON.stringify(payload)});await load(token);removeReporterMutation(mutation.id);setMessage("Resultatet är sparat. Matchhändelserna nedan är nu öppna för färdigspelade matcher.")}
  catch(reason){if(isNetworkError(reason)){upsertReporterMutation({...mutation,state:"uncertain"});optimisticResult(match,payload);setMessage("Sparstatus osäker. Inmatningen är bevarad lokalt och stäms av mot servern när nätet återkommer.")}else setError(reason instanceof Error?reason.message:"Resultatet kunde inte sparas.")}
  finally{setBusy(false)}
 }
 const pendingResults=useMemo(()=>new Set(readReporterQueue().filter(isResultMutation).filter(item=>item.cupId===cupInfo?.id).map(item=>item.matchId)),[cupInfo?.id,pending,matches]);

 if(!token)return <main className="reporter-page reporter-page--login"><header className="reporter-hero"><p className="kicker">CN//REPORTER</p><h1>Matchrapportör</h1><p>Logga in med den fyrsiffriga kod du fått av arrangören.</p></header><form className="admin-panel reporter-login" onSubmit={login}><div className="reporter-login__fields"><label><span>Cup</span>{linkedCup?<div className="reporter-linked-cup"><strong>Cupen är vald via inloggningslänken</strong><small>Den tekniska länkkoden döljs här.</small></div>:<input value={cup} onChange={event=>setCup(event.target.value)} required placeholder="Cupens länk eller ID"/>}</label><label><span>4-siffrig kod</span><input inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={code} onChange={event=>setCode(event.target.value.replace(/\D/g,"").slice(0,4))} required placeholder="0000" autoComplete="one-time-code"/></label></div>{error&&<p className="reporter-alert reporter-alert--error" role="alert">{error}</p>}<div className="reporter-login__footer"><span>Koden skapas av cupadministratören.</span><button className="is-primary" disabled={busy||code.length!==4}>{busy?"Kontrollerar…":"Öppna matchrapportering"}</button></div></form></main>;
 if(!cupInfo)return <main className="reporter-page"><div className="reporter-network is-syncing" role="status"><span/><strong>Öppnar rapportering…</strong></div></main>;
 return <main className="reporter-page">
  <div className={`reporter-network is-${online?syncing?"syncing":"online":"offline"}`} role="status" aria-live="polite"><span aria-hidden="true"/><strong>{online?syncing?"Synkroniserar":"Online":"Offline"}</strong><small>{pending?`${pending} ändring${pending===1?"":"ar"} väntar`:online?"Alla ändringar är synkroniserade":"Inmatningar sparas på mobilen"}</small>{online&&pending>0&&<button type="button" onClick={()=>void flushResults()} disabled={syncing}>Synka nu</button>}</div>
  <header className="reporter-hero reporter-hero--session"><div><p className="kicker">CN//REPORTER</p><h1>{cupInfo?.name||"Matchrapportering"}</h1><p>Rapportera slutresultat först. Lägg sedan till målskyttar, assist och kort.</p></div><div className="reporter-hero__actions">{cupInfo?.public_slug&&<a href={`/cup/${encodeURIComponent(cupInfo.public_slug)}?from=reporter`}>Se turneringsvyn →</a>}<button type="button" onClick={logout}>Logga ut</button></div></header>
  {(error||message)&&<section className={`reporter-alert ${error?"reporter-alert--error":"reporter-alert--success"}`} role={error?"alert":"status"}><strong>{error?"Något gick fel":online?"Status":"Offline"}</strong><span>{error||message}</span></section>}
  <section className="admin-panel reporter-results"><div className="admin-panel__top"><span>1 / RESULTAT</span><strong>{matches.length} MATCHER</strong></div><div className="reporter-results__head"><div><h2>Rapportera resultat</h2><p>Fyll i båda lagens mål och spara matchen.</p></div><span className="admin-lock">REPORTER</span></div><div className="reporter-match-list">{matches.map(match=><ReporterMatch key={match.id} m={match} busy={busy} pending={pendingResults.has(match.id)} save={save}/>)}</div></section>
  <ReporterMatchEvents token={token} cupId={cupInfo.id} online={online} queueSignal={pending} onAuthError={logout}/>
 </main>;
}

function ReporterMatch({m,busy,pending,save}:{m:Match;busy:boolean;pending:boolean;save:(m:Match,h:string,a:string,hp:string,ap:string)=>void}){
 const[h,setH]=useState(m.home_score==null?"":String(m.home_score)),[a,setA]=useState(m.away_score==null?"":String(m.away_score));const[hp,setHp]=useState(m.home_penalties==null?"":String(m.home_penalties)),[ap,setAp]=useState(m.away_penalties==null?"":String(m.away_penalties));
 useEffect(()=>{setH(m.home_score==null?"":String(m.home_score));setA(m.away_score==null?"":String(m.away_score));setHp(m.home_penalties==null?"":String(m.home_penalties));setAp(m.away_penalties==null?"":String(m.away_penalties))},[m]);
 const tied=m.stage!=="Gruppspel"&&h!==""&&a!==""&&Number(h)===Number(a),saved=m.status==="played";
 return <article className={`reporter-match${saved?" is-saved":""}${pending?" is-pending":""}`}><div className="reporter-match__meta"><span>{m.scheduled_start?.replace("T"," ")||"Ej schemalagd"}</span><span>{m.stage||"Match"}</span>{pending?<span className="reporter-match__pending">Väntar på nät</span>:saved&&<span className="reporter-match__saved">Sparad</span>}</div><div className="reporter-match__body"><div className="reporter-match__teams"><strong>{m.home_team}</strong><span>mot</span><strong>{m.away_team}</strong></div><div className="reporter-score" aria-label={`${m.home_team} mot ${m.away_team}`}><label><span>{m.home_team}</span><input aria-label={`Mål för ${m.home_team}`} inputMode="numeric" type="number" min="0" value={h} onChange={event=>setH(event.target.value)}/></label><b>–</b><label><span>{m.away_team}</span><input aria-label={`Mål för ${m.away_team}`} inputMode="numeric" type="number" min="0" value={a} onChange={event=>setA(event.target.value)}/></label>{tied&&<div className="reporter-penalties"><label>Straffar hemma<input aria-label="Hemmastraffar" inputMode="numeric" type="number" min="0" value={hp} onChange={event=>setHp(event.target.value)} placeholder="0"/></label><label>Straffar borta<input aria-label="Bortastraffar" inputMode="numeric" type="number" min="0" value={ap} onChange={event=>setAp(event.target.value)} placeholder="0"/></label></div>}<button type="button" disabled={busy||h===""||a===""||(tied&&(hp===""||ap===""))} onClick={()=>save(m,h,a,hp,ap)}>{pending?"Uppdatera lokalt":saved?"Uppdatera":"Spara resultat"}</button></div></div></article>;
}
