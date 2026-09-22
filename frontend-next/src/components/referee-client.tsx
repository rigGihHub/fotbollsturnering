"use client";

import {FormEvent,useCallback,useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";

const API=CLIENT_API_BASE,KEY="cupnavi_referee_session_v1",SESSION_CACHE="cupnavi_referee_assignment_cache_v1";

type Cup={id:number;name:string;public_slug?:string|null};
type Referee={id:number;name:string};
type Match={id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;pitch_number?:number|string|null;home_team:string;away_team:string;home_score:number|null;away_score:number|null;home_penalties?:number|null;away_penalties?:number|null;played?:boolean};
type AssignmentPayload={referee:Referee;matches:Match[]};
type CachedSession={cup:Cup;referee:Referee;matches:Match[]};

async function call<T>(path:string,token?:string|null,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);if(token)headers.set("Authorization",`Bearer ${token}`);if(init.body)headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);return payload as T;
}

function readCache():CachedSession|null{try{return JSON.parse(localStorage.getItem(SESSION_CACHE)||"null") as CachedSession|null}catch{return null}}
function writeCache(data:CachedSession){localStorage.setItem(SESSION_CACHE,JSON.stringify(data))}

export default function RefereeClient(){
 const[cup,setCup]=useState(""),[linkedCup,setLinkedCup]=useState(false),[refereeId,setRefereeId]=useState(""),[code,setCode]=useState("");
 const[token,setToken]=useState<string|null>(null),[cupInfo,setCupInfo]=useState<Cup|null>(null),[referee,setReferee]=useState<Referee|null>(null),[matches,setMatches]=useState<Match[]>([]);
 const[busy,setBusy]=useState(false),[online,setOnline]=useState(true),[error,setError]=useState(""),[message,setMessage]=useState("");
 const logout=useCallback(()=>{localStorage.removeItem(KEY);setToken(null);setCupInfo(null);setReferee(null);setMatches([]);setMessage("");setError("")},[]);
 const remember=useCallback((nextCup:Cup,nextReferee:Referee,nextMatches:Match[])=>writeCache({cup:nextCup,referee:nextReferee,matches:nextMatches}),[]);
 const load=useCallback(async(sessionToken:string)=>{
  const[session,assignments]=await Promise.all([call<{cup:Cup;referee:Referee}>("/api/referee/session",sessionToken),call<AssignmentPayload>("/api/referee/assignments",sessionToken)]);
  const next=assignments.matches||[];setCupInfo(session.cup);setReferee(session.referee);setMatches(next);remember(session.cup,session.referee,next);
 },[remember]);
 useEffect(()=>{const refresh=()=>setOnline(navigator.onLine);refresh();window.addEventListener("online",refresh);window.addEventListener("offline",refresh);return()=>{window.removeEventListener("online",refresh);window.removeEventListener("offline",refresh)}},[]);
 useEffect(()=>{
  const query=new URLSearchParams(window.location.search);const queryCup=query.get("cup"),queryReferee=query.get("referee");
  if(queryCup){setCup(queryCup);setLinkedCup(true)} if(queryReferee)setRefereeId(queryReferee.replace(/\D/g,""));
  const stored=localStorage.getItem(KEY);if(!stored)return;setToken(stored);
  void load(stored).catch(()=>{const cached=readCache();const cacheMatchesLink=!queryCup||queryCup===cached?.cup.public_slug||queryCup===String(cached?.cup.id);if(!navigator.onLine&&cached&&cacheMatchesLink){setCupInfo(cached.cup);setReferee(cached.referee);setMatches(cached.matches);setMessage("Offline: dina senast hämtade matcher visas.")}else logout()});
 },[load,logout]);
 async function login(event:FormEvent){event.preventDefault();setBusy(true);setError("");setMessage("");try{const result=await call<{token:string;cup:Cup;referee:Referee}>("/api/referee/session",null,{method:"POST",body:JSON.stringify({cup,referee_id:Number(refereeId),code})});localStorage.setItem(KEY,result.token);setToken(result.token);setCupInfo(result.cup);setReferee(result.referee);setCode("");await load(result.token)}catch(reason){setError(reason instanceof Error?reason.message:"Domarinloggningen misslyckades.")}finally{setBusy(false)}}
 async function save(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string){
  if(!token||!cupInfo||!referee)return;setBusy(true);setError("");setMessage("");
  const payload={home_score:Number(home),away_score:Number(away),home_penalties:homePenalties===""?null:Number(homePenalties),away_penalties:awayPenalties===""?null:Number(awayPenalties),expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null};
  try{await call(`/api/referee/assignments/matches/${match.id}`,token,{method:"PUT",body:JSON.stringify(payload)});await load(token);setMessage("Resultatet är sparat.")}catch(reason){setError(reason instanceof Error?reason.message:"Resultatet kunde inte sparas.")}finally{setBusy(false)}
 }
 const nextMatch=useMemo(()=>matches.find(match=>!match.played)||matches[0]||null,[matches]);
 if(!token)return <main className="reporter-page reporter-page--login referee-page"><header className="reporter-hero"><p className="kicker">CN//REFEREE</p><h1>Domarvy</h1><p>Logga in med cupens domarlänk, ditt domar-ID och din fyrsiffriga kod. Du ser bara dina tilldelade matcher.</p></header><form className="admin-panel reporter-login" onSubmit={login}><div className="reporter-login__fields"><label><span>Cup</span>{linkedCup?<div className="reporter-linked-cup"><strong>Cupen är vald via länken</strong><small>Domarkoden gäller bara denna cup.</small></div>:<input value={cup} onChange={event=>setCup(event.target.value)} required placeholder="Cupens länk eller ID"/>}</label><label><span>Domar-ID</span><input inputMode="numeric" value={refereeId} onChange={event=>setRefereeId(event.target.value.replace(/\D/g,""))} required placeholder="Ex. 12"/></label><label><span>4-siffrig kod</span><input inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={code} onChange={event=>setCode(event.target.value.replace(/\D/g,"").slice(0,4))} required placeholder="0000" autoComplete="one-time-code"/></label></div>{error&&<p className="reporter-alert reporter-alert--error" role="alert">{error}</p>}<div className="reporter-login__footer"><span>Koden skapas av arrangören under Domare.</span><button className="is-primary" disabled={busy||code.length!==4||!refereeId}>{busy?"Kontrollerar...":"Öppna domarvyn"}</button></div></form></main>;
 return <main className="reporter-page referee-page">
  <div className={`reporter-network is-${online?"online":"offline"}`} role="status" aria-live="polite"><span aria-hidden="true"/><strong>{online?"Online":"Offline"}</strong><small>{online?"Resultat sparas mot servern":"Du kan se senast hämtade matcher men inte spara nya resultat"}</small></div>
  <header className="reporter-hero reporter-hero--session"><div><p className="kicker">CN//REFEREE</p><h1>{referee?.name||"Domare"}</h1><p>{cupInfo?.name||"Cup"} · {matches.length} tilldelade matcher</p></div><div className="reporter-hero__actions">{cupInfo?.public_slug&&<a href={`/cup/${encodeURIComponent(cupInfo.public_slug)}`}>Se publik vy →</a>}<button type="button" onClick={logout}>Logga ut</button></div></header>
  {(error||message)&&<section className={`reporter-alert ${error?"reporter-alert--error":"reporter-alert--success"}`} role={error?"alert":"status"}><strong>{error?"Något gick fel":"Klart"}</strong><span>{error||message}</span></section>}
  {nextMatch&&<section className="reporter-live is-live"><div className="reporter-live__top"><div><span>NÄSTA UPPDRAG</span><h2>{nextMatch.home_team} - {nextMatch.away_team}</h2></div><strong>{nextMatch.played?"RAPPORTERAD":"RESULTAT"}</strong></div><div className="reporter-live__status-actions"><span>{[nextMatch.scheduled_start?.replace("T"," "),nextMatch.pitch_number?`Plan ${nextMatch.pitch_number}`:null,nextMatch.stage].filter(Boolean).join(" · ")||"Tid saknas"}</span></div></section>}
  <section className="admin-panel reporter-results"><div className="admin-panel__top"><span>DOMARE / RESULTAT</span><strong>{matches.length} MATCHER</strong></div><div className="reporter-results__head"><div><h2>Mina matcher</h2><p>Rapportera slutresultat för matcher du är tilldelad.</p></div><span className="admin-lock">DOMARE</span></div><div className="reporter-match-list">{matches.map(match=><RefereeMatch key={match.id} match={match} busy={busy||!online} save={save}/>)}</div>{matches.length===0&&<div className="admin-empty"><strong>Inga matcher tilldelade</strong><span>Kontakta arrangören om du saknar matcher.</span></div>}</section>
 </main>;
}

function RefereeMatch({match,busy,save}:{match:Match;busy:boolean;save:(match:Match,h:string,a:string,hp:string,ap:string)=>void}){
 const[h,setH]=useState(match.home_score==null?"":String(match.home_score)),[a,setA]=useState(match.away_score==null?"":String(match.away_score)),[hp,setHp]=useState(match.home_penalties==null?"":String(match.home_penalties)),[ap,setAp]=useState(match.away_penalties==null?"":String(match.away_penalties));
 useEffect(()=>{setH(match.home_score==null?"":String(match.home_score));setA(match.away_score==null?"":String(match.away_score));setHp(match.home_penalties==null?"":String(match.home_penalties));setAp(match.away_penalties==null?"":String(match.away_penalties))},[match]);
 const tied=match.stage!=="Gruppspel"&&h!==""&&a!==""&&Number(h)===Number(a);
 return <article className={`reporter-match${match.played?" is-saved":""}`}><div className="reporter-match__meta"><span>{match.scheduled_start?.replace("T"," ")||"Ej schemalagd"}</span><span>{match.pitch_number?`Plan ${match.pitch_number}`:"Plan saknas"}</span>{match.played&&<span className="reporter-match__saved">Sparad</span>}</div><div className="reporter-match__body"><div className="reporter-match__teams"><strong>{match.home_team}</strong><span>mot</span><strong>{match.away_team}</strong></div><div className="reporter-score"><label><span>{match.home_team}</span><input aria-label={`Mål för ${match.home_team}`} inputMode="numeric" type="number" min="0" value={h} onChange={event=>setH(event.target.value)}/></label><b>-</b><label><span>{match.away_team}</span><input aria-label={`Mål för ${match.away_team}`} inputMode="numeric" type="number" min="0" value={a} onChange={event=>setA(event.target.value)}/></label>{tied&&<div className="reporter-penalties"><label>Straffar hemma<input inputMode="numeric" type="number" min="0" value={hp} onChange={event=>setHp(event.target.value)}/></label><label>Straffar borta<input inputMode="numeric" type="number" min="0" value={ap} onChange={event=>setAp(event.target.value)}/></label></div>}<button type="button" disabled={busy||h===""||a===""||(tied&&(hp===""||ap===""))} onClick={()=>save(match,h,a,hp,ap)}>{match.played?"Uppdatera resultat":"Spara resultat"}</button></div></div></article>;
}
