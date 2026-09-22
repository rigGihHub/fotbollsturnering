"use client";

import {useCallback,useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";
import {EventValues,isEventMutation,isNetworkError,readReporterCache,readReporterQueue,removeReporterMutation,sameEventValues,updateReporterMutation,upsertReporterMutation,writeReporterCache} from "../lib/reporter-offline";

const API=CLIENT_API_BASE;
type EventMatch={id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_id:number;away_team_id:number;home_team_name:string;away_team_name:string;home_score:number;away_score:number};
type Player=EventValues&{id:number;name:string;player_number?:number|null};
type Team={side:"home"|"away";team_id:number;team_name:string;team_score:number;players:Player[];registered_goals:number;registered_assists:number};
type Detail={match:{id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_name:string;away_team_name:string;home_score:number;away_score:number};enabled:{assists:boolean;cards:boolean};teams:Team[]};

async function req<T>(path:string,token:string,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);headers.set("Authorization",`Bearer ${token}`);if(init.body)headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);return payload as T;
}
function values(player:Player):EventValues{return {goals:player.goals||0,assists:player.assists||0,yellow_cards:player.yellow_cards||0,red_cards:player.red_cards||0}}
function eventLabel(field:keyof EventValues){return field==="goals"?"mål":field==="assists"?"assist":field==="yellow_cards"?"gult kort":"rött kort"}
const matchesCache=(cupId:number)=>`events-matches-${cupId}`,detailCache=(cupId:number,matchId:number)=>`events-detail-${cupId}-${matchId}`;

export default function ReporterMatchEvents({token,cupId,online,queueSignal,onAuthError}:{token:string;cupId:number;online:boolean;queueSignal:number;onAuthError?:()=>void}){
 const[matches,setMatches]=useState<EventMatch[]>([]),[matchId,setMatchId]=useState<number|null>(null),[detail,setDetail]=useState<Detail|null>(null);
 const[busyKey,setBusyKey]=useState(""),[error,setError]=useState(""),[message,setMessage]=useState("");
 const handleError=useCallback((err:unknown,fallback:string)=>{const text=err instanceof Error?err.message:fallback;if(/session expired|authentication required/i.test(text))onAuthError?.();setError(text)},[onAuthError]);
 const loadMatches=useCallback(async()=>{try{const payload=await req<{matches:EventMatch[]}>("/api/reporter/reporting/events",token);const next=payload.matches||[];setMatches(next);writeReporterCache(matchesCache(cupId),next);setMatchId(current=>current&&next.some(m=>m.id===current)?current:(next[0]?.id??null));setError("")}catch(err){const cached=readReporterCache<EventMatch[]>(matchesCache(cupId));if(!navigator.onLine&&cached){setMatches(cached);setMatchId(current=>current??cached[0]?.id??null);setMessage("Offline: senast hämtade matchhändelser visas.")}else handleError(err,"Matchhändelser kunde inte hämtas.")}},[cupId,handleError,token]);
 useEffect(()=>{void loadMatches()},[loadMatches]);
 useEffect(()=>{
  if(!matchId){setDetail(null);return}let cancelled=false;
  if(!navigator.onLine){setDetail(readReporterCache<Detail>(detailCache(cupId,matchId)));return}
  req<Detail>(`/api/reporter/reporting/matches/${matchId}/events`,token).then(payload=>{if(!cancelled){setDetail(payload);writeReporterCache(detailCache(cupId,matchId),payload);setError("")}}).catch(err=>{if(!cancelled){const cached=readReporterCache<Detail>(detailCache(cupId,matchId));if(cached)setDetail(cached);else handleError(err,"Matchen kunde inte hämtas.")}});return()=>{cancelled=true};
 },[cupId,handleError,matchId,token]);

 const applyPlayer=useCallback((playerId:number,next:EventValues)=>setDetail(current=>{
  if(!current)return current;const updated={...current,teams:current.teams.map(team=>({...team,players:team.players.map(player=>player.id===playerId?{...player,...next}:player)}))};writeReporterCache(detailCache(cupId,current.match.id),updated);return updated;
 }),[cupId]);
 const flushEvents=useCallback(async()=>{
  if(!online)return;const queued=readReporterQueue().filter(isEventMutation).filter(item=>item.cupId===cupId&&item.state!=="conflict");if(!queued.length)return;
  for(const mutation of queued){
   try{
    const server=await req<Detail>(`/api/reporter/reporting/matches/${mutation.matchId}/events`,token);const player=server.teams.flatMap(team=>team.players).find(item=>item.id===mutation.playerId);if(!player){updateReporterMutation(mutation.id,{state:"conflict"});continue}
    const current=values(player),desired={goals:mutation.payload.goals,assists:mutation.payload.assists,yellow_cards:mutation.payload.yellow_cards,red_cards:mutation.payload.red_cards};
    if(sameEventValues(current,desired)){removeReporterMutation(mutation.id);if(detail?.match.id===mutation.matchId)applyPlayer(mutation.playerId,desired);continue}
    if(!sameEventValues(current,mutation.payload.expected)){updateReporterMutation(mutation.id,{state:"conflict"});setError("En offlinehändelse krockar med nyare serverdata och har inte skrivits över.");continue}
    const saved=await req<Detail>(`/api/reporter/reporting/matches/${mutation.matchId}/events/${mutation.playerId}`,token,{method:"PUT",body:JSON.stringify({...desired,expected:mutation.payload.expected})});removeReporterMutation(mutation.id);writeReporterCache(detailCache(cupId,mutation.matchId),saved);if(detail?.match.id===mutation.matchId)setDetail(saved);
   }catch(err){if(!isNetworkError(err))handleError(err,"Offlinehändelsen kunde inte synkroniseras.");break}
  }
 },[applyPlayer,cupId,detail?.match.id,handleError,online,token]);
 useEffect(()=>{if(!online||queueSignal===0)return;const retry=window.setTimeout(()=>void flushEvents(),1800);return()=>window.clearTimeout(retry)},[online,queueSignal,flushEvents]);

 const selected=useMemo(()=>matches.find(match=>match.id===matchId)||null,[matches,matchId]);
 async function change(player:Player,field:keyof EventValues,delta:number){
  if(!detail)return;const previous=values(player);const next={...previous,[field]:Math.max(0,previous[field]+delta)};if(next[field]===previous[field])return;
  const id=`event-${cupId}-${detail.match.id}-${player.id}`,mutation={id,kind:"event" as const,cupId,matchId:detail.match.id,playerId:player.id,createdAt:Date.now(),state:"queued" as const,payload:{...next,expected:previous}};setError("");setMessage("");
  if(!navigator.onLine){upsertReporterMutation(mutation);applyPlayer(player.id,next);setMessage(`${player.name}: ${eventLabel(field)} sparat lokalt.`);return}
  const key=`${player.id}-${field}`;setBusyKey(key);
  try{const payload=await req<Detail>(`/api/reporter/reporting/matches/${detail.match.id}/events/${player.id}`,token,{method:"PUT",body:JSON.stringify({...next,expected:previous})});setDetail(payload);writeReporterCache(detailCache(cupId,detail.match.id),payload);removeReporterMutation(id);setMessage(`${player.name}: ${eventLabel(field)} uppdaterat.`)}
  catch(err){if(isNetworkError(err)){upsertReporterMutation({...mutation,state:"uncertain"});applyPlayer(player.id,next);setMessage("Sparstatus osäker. Händelsen är bevarad lokalt och stäms av när nätet återkommer.")}else{handleError(err,"Händelsen kunde inte sparas.");if(matchId)try{setDetail(await req<Detail>(`/api/reporter/reporting/matches/${matchId}/events`,token))}catch{}}}
  finally{setBusyKey("")}
 }

 return <section className="admin-panel reporter-events" id="reporter-events">
  <div className="admin-panel__top"><span>MATCHHÄNDELSER</span><strong>SNABBINMATNING</strong></div>
  <div className="reporter-events__head"><div><h2>Målskyttar, assist & kort</h2><p>Välj en färdigspelad match. Varje tryck sparas direkt eller läggs tryggt i offlinekön.</p></div><span className="admin-lock">STEG 2</span></div>
  {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:14}} role={error?"alert":"status"}><b>{error?"Fel":online?"Sparat":"Offline"}</b> · {error||message}</div>}
  {matches.length?<label className="reporter-events__picker"><span>Färdigspelad match</span><select value={matchId??""} onChange={event=>setMatchId(Number(event.target.value))}>{matches.map(match=><option key={match.id} value={match.id}>{match.home_team_name} – {match.away_team_name} · {match.home_score}–{match.away_score}</option>)}</select></label>:<div className="admin-empty"><strong>Inga färdigspelade matcher ännu</strong><span>Spara ett matchresultat först. Då blir målskyttar, assist och kort tillgängliga här.</span></div>}
  {selected&&detail&&<><div className="reporter-events__selected"><span>VALD MATCH</span><strong>{selected.home_team_name} {selected.home_score}–{selected.away_score} {selected.away_team_name}</strong><small>{selected.stage||"Match"}</small></div><div className="reporter-events__teams">{detail.teams.map(team=><section key={team.team_id} className="reporter-event-team"><header><div><span>{team.side==="home"?"HEMMA":"BORTA"}</span><h3>{team.team_name}</h3></div><strong>{team.registered_goals}/{team.team_score} mål kopplade</strong></header>{team.players.length?<div className="reporter-player-list">{team.players.map(player=><article key={player.id}><div><strong>{player.player_number!=null?`${player.player_number}. `:""}{player.name}</strong><small>{player.goals} mål{detail.enabled.assists?` · ${player.assists} assist`:""}{detail.enabled.cards?` · ${player.yellow_cards} gula · ${player.red_cards} röda`:""}</small></div><div className="reporter-player-actions"><Counter label="Mål" value={player.goals} disabled={!!busyKey} minus={()=>void change(player,"goals",-1)} plus={()=>void change(player,"goals",1)}/>{detail.enabled.assists&&<Counter label="Assist" value={player.assists} disabled={!!busyKey} minus={()=>void change(player,"assists",-1)} plus={()=>void change(player,"assists",1)}/>} {detail.enabled.cards&&<><Counter label="Gult" value={player.yellow_cards} disabled={!!busyKey} minus={()=>void change(player,"yellow_cards",-1)} plus={()=>void change(player,"yellow_cards",1)}/><Counter label="Rött" value={player.red_cards} disabled={!!busyKey} minus={()=>void change(player,"red_cards",-1)} plus={()=>void change(player,"red_cards",1)}/></>}</div></article>)}</div>:<div className="reporter-events__empty"><strong>Trupp saknas</strong><span>Lägg in spelarna i lagets trupp för att kunna koppla mål och kort.</span></div>}{team.registered_goals<team.team_score&&<p className="reporter-events__warning">{team.team_score-team.registered_goals} mål saknar spelarkoppling, exempelvis självmål eller okänd målskytt.</p>}</section>)}</div></>}
 </section>;
}

function Counter({label,value,disabled,minus,plus}:{label:string;value:number;disabled:boolean;minus:()=>void;plus:()=>void}){
 return <span className="reporter-counter"><small>{label}</small><button type="button" aria-label={`Minska ${label}`} disabled={disabled||value<=0} onClick={minus}>−</button><strong aria-live="polite">{value}</strong><button type="button" aria-label={`Öka ${label}`} disabled={disabled} onClick={plus}>+</button></span>;
}
