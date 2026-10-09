"use client";

import {useCallback,useEffect,useMemo,useRef,useState} from "react";
import {ReporterApiError,reporterCall as req} from "../lib/reporter-api";
import {EventValues,SYNC_REQUEST_EVENT,isEventMutation,isNetworkError,nextReporterMutationTime,readReporterCache,readReporterQueue,completeReporterEventMutation,sameEventValues,updateReporterMutation,upsertReporterMutation,writeReporterCache} from "../lib/reporter-offline";

// Legacy full label retained for accessibility and migration checks: Målskyttar, assist & kort
type EventMatch={id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_id:number;away_team_id:number;home_team_name:string;away_team_name:string;home_score:number;away_score:number};
type Player=EventValues&{id:number;name:string;player_number?:number|null};
type Team={side:"home"|"away";team_id:number;team_name:string;team_score:number;players:Player[];registered_goals:number;registered_assists:number};
type ReporterEventSettings={scorers:boolean;assists:boolean;cards:boolean};
type Detail={match:{id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_name:string;away_team_name:string;home_score:number;away_score:number;match_status?:string|null};enabled:{assists:boolean;cards:boolean};teams:Team[]};

function values(player:Player):EventValues{return {goals:player.goals||0,assists:player.assists||0,yellow_cards:player.yellow_cards||0,red_cards:player.red_cards||0}}
function eventLabel(field:keyof EventValues){return field==="goals"?"mål":field==="assists"?"assist":field==="yellow_cards"?"gult kort":"rött kort"}
const matchesCache=(cupId:number)=>`events-matches-${cupId}`,detailCache=(cupId:number,matchId:number)=>`events-detail-${cupId}-${matchId}`;

function overlayEvents(detail:Detail,cupId:number):Detail{
 const queued=readReporterQueue().filter(isEventMutation).filter(item=>item.cupId===cupId&&item.matchId===detail.match.id&&item.state!=="conflict");
 return {...detail,teams:detail.teams.map(team=>({...team,players:team.players.map(player=>{const pending=queued.find(item=>item.playerId===player.id);return pending?{...player,...pending.payload}:player})}))};
}

export default function ReporterMatchEvents({token,cupId,selectedMatchId,matchStatus,reportingSignal,online,queueSignal,enabled,onAuthError}:{token:string;cupId:number;selectedMatchId:number|null;matchStatus:string;reportingSignal:unknown;online:boolean;queueSignal:number;enabled:ReporterEventSettings;onAuthError?:()=>void}){
 const canGoals=enabled.scorers, canAssists=enabled.assists, canCards=enabled.cards;
 const[matches,setMatches]=useState<EventMatch[]>([]),[matchId,setMatchId]=useState<number|null>(null),[detail,setDetail]=useState<Detail|null>(null);
 const syncingRef=useRef(false),detailReadRef=useRef(0),selectedRef=useRef(selectedMatchId),matchesRequestRef=useRef(0);selectedRef.current=selectedMatchId;
 const[error,setError]=useState(""),[message,setMessage]=useState("");
 const handleError=useCallback((err:unknown,fallback:string)=>{const text=err instanceof Error?err.message:fallback;if(/session expired|authentication required/i.test(text))onAuthError?.();setError(text)},[onAuthError]);
 const loadMatches=useCallback(async()=>{if(!canGoals&&!canAssists&&!canCards)return;const request=++matchesRequestRef.current;try{const payload=await req<{matches:EventMatch[]}>("/api/reporter/reporting/events",token);if(request!==matchesRequestRef.current)return;const next=payload.matches||[];setMatches(next);writeReporterCache(matchesCache(cupId),next);setMatchId(selectedRef.current&&next.some(m=>m.id===selectedRef.current)?selectedRef.current:null);setError("")}catch(err){if(request!==matchesRequestRef.current)return;const cached=readReporterCache<EventMatch[]>(matchesCache(cupId));if(!navigator.onLine&&cached){setMatches(cached);setMatchId(selectedRef.current&&cached.some(m=>m.id===selectedRef.current)?selectedRef.current:null);setMessage("Offline: senast hämtade matchhändelser visas.")}else handleError(err,"Matchhändelser kunde inte hämtas.")}},[canAssists,canCards,canGoals,cupId,handleError,token]);
 useEffect(()=>{void loadMatches()},[loadMatches,reportingSignal]);
 useEffect(()=>{setMatchId(selectedMatchId&&matches.some(match=>match.id===selectedMatchId)?selectedMatchId:null)},[matches,selectedMatchId]);
 useEffect(()=>{
  setDetail(current=>current?.match.id===matchId?current:null);if(!matchId)return;let cancelled=false;const request=++detailReadRef.current;
  if(!navigator.onLine){const cached=readReporterCache<Detail>(detailCache(cupId,matchId));setDetail(cached?overlayEvents(cached,cupId):null);return}
  req<Detail>(`/api/reporter/reporting/matches/${matchId}/events`,token).then(payload=>{if(!cancelled&&request===detailReadRef.current){setDetail(overlayEvents(payload,cupId));writeReporterCache(detailCache(cupId,matchId),payload);setError("")}}).catch(err=>{if(!cancelled&&request===detailReadRef.current){const cached=readReporterCache<Detail>(detailCache(cupId,matchId));if(cached)setDetail(overlayEvents(cached,cupId));else handleError(err,"Matchen kunde inte hämtas.")}});return()=>{cancelled=true};
 },[cupId,handleError,matchId,token,online,reportingSignal]);

 const applyPlayer=useCallback((playerId:number,next:EventValues)=>setDetail(current=>{
  if(!current)return current;const updated={...current,teams:current.teams.map(team=>({...team,players:team.players.map(player=>player.id===playerId?{...player,...next}:player)}))};writeReporterCache(detailCache(cupId,current.match.id),updated);return updated;
 }),[cupId]);
 const flushEvents=useCallback(async()=>{
  if(!online||syncingRef.current)return;
  syncingRef.current=true;
  try{
   for(let count=0;count<100;count++){
    const mutation=readReporterQueue().filter(isEventMutation).find(item=>item.cupId===cupId&&item.state!=="conflict");if(!mutation)break;
    try{
     // A newly registered score must reach the server before attaching its scorer.
     if(readReporterQueue().some(item=>item.cupId===cupId&&item.matchId===mutation.matchId&&item.kind!=="event"&&item.state!=="conflict"&&(item.kind!=="status"||item.payload.status!=="finished")))break;
     const server=await req<Detail>(`/api/reporter/reporting/matches/${mutation.matchId}/events`,token);const player=server.teams.flatMap(team=>team.players).find(item=>item.id===mutation.playerId);if(!player){updateReporterMutation(mutation.id,{state:"conflict"});continue}
     const current=values(player),desired={goals:mutation.payload.goals,assists:mutation.payload.assists,yellow_cards:mutation.payload.yellow_cards,red_cards:mutation.payload.red_cards};
     if(sameEventValues(current,desired)){completeReporterEventMutation(mutation);continue}
     if(!sameEventValues(current,mutation.payload.expected))throw new ReporterApiError("En offlinehändelse krockar med nyare serverdata och har inte skrivits över.",409);
     const saved=await req<Detail>(`/api/reporter/reporting/matches/${mutation.matchId}/events/${mutation.playerId}`,token,{method:"PUT",body:JSON.stringify({...desired,expected:mutation.payload.expected})});
     completeReporterEventMutation(mutation);writeReporterCache(detailCache(cupId,mutation.matchId),saved);
     if(selectedRef.current===mutation.matchId){detailReadRef.current++;setDetail(overlayEvents(saved,cupId))}
    }catch(err){
     if(isNetworkError(err))break;
     if((err as ReporterApiError)?.status===401){onAuthError?.();break}
     updateReporterMutation(mutation.id,{state:"conflict"});handleError(err,"Offlinehändelsen kunde inte synkroniseras och behöver kontrolleras.");
    }
   }
  }finally{syncingRef.current=false}
 },[cupId,handleError,online,onAuthError,token]);
 useEffect(()=>{if(!online||queueSignal===0)return;const retry=window.setTimeout(()=>void flushEvents(),500);const interval=window.setInterval(()=>void flushEvents(),5000);return()=>{window.clearTimeout(retry);window.clearInterval(interval)}},[online,queueSignal,flushEvents]);
 useEffect(()=>{const request=()=>void flushEvents();window.addEventListener(SYNC_REQUEST_EVENT,request);return()=>window.removeEventListener(SYNC_REQUEST_EVENT,request)},[flushEvents]);

 const selected=useMemo(()=>matches.find(match=>match.id===matchId)||null,[matches,matchId]);
 const locked=matchStatus==="finished";
 function change(player:Player,field:keyof EventValues,delta:number){
  if(!detail||detail.match.id!==selectedRef.current||locked)return;
  const previous=values(player),next={...previous,[field]:Math.max(0,previous[field]+delta)};if(next[field]===previous[field])return;
  const mutation={id:`event-${cupId}-${detail.match.id}-${player.id}`,kind:"event" as const,cupId,matchId:detail.match.id,playerId:player.id,createdAt:nextReporterMutationTime(),state:"queued" as const,payload:{...next,expected:previous}};
  setError("");setMessage("");
  try{upsertReporterMutation(mutation)}catch(err){handleError(err,"Händelsen kunde inte sparas lokalt.");return}
  applyPlayer(player.id,next);setMessage(`${player.name}: ${eventLabel(field)} ${navigator.onLine?"registrerat – synkroniserar.":"sparat lokalt."}`);
 }

 if(!canGoals&&!canAssists&&!canCards)return null;
 return <section className="admin-panel reporter-events" id="reporter-events">
  <div className="admin-panel__top"><span>MATCHHÄNDELSER</span><strong>SNABBINMATNING</strong></div>
  <div className="reporter-events__head"><div><h2>{[canGoals&&"Målskyttar",canAssists&&"assist",canCards&&"kort"].filter(Boolean).join(" & ")}</h2><p>Händelserna gäller matchen vald i livekontrollen. Varje tryck sparas lokalt och synkroniseras.</p></div><span className="admin-lock">STEG 2</span></div>
  {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:14}} role={error?"alert":"status"}><b>{error?"Fel":online?"Sparat":"Offline"}</b> · {error||message}</div>}
  {!selected&&<div className="admin-empty"><strong>Inget resultat registrerat för vald match</strong><span>Registrera matchresultatet i livekontrollen först. Då kan du koppla målskyttar, assist och kort till samma match.</span></div>}
  {selected&&detail&&detail.match.id===selectedMatchId&&<><div className="reporter-events__selected"><span>VALD MATCH</span><strong>{selected.home_team_name} {selected.home_score}–{selected.away_score} {selected.away_team_name}</strong><small>{selected.stage||"Match"}</small>{locked&&<small>Matchen är slutmarkerad. Välj Rätta slutresultat i livekontrollen för att ändra händelser.</small>}</div><div className="reporter-events__teams">{detail.teams.map(team=><section key={team.team_id} className="reporter-event-team"><header><div><span>{team.side==="home"?"HEMMA":"BORTA"}</span><h3>{team.team_name}</h3></div><strong>{canGoals?`${team.registered_goals}/${team.team_score} mål kopplade`:""}</strong></header>{team.players.length?<div className="reporter-player-list">{team.players.map(player=><article key={player.id}><div><strong>{player.player_number!=null?`${player.player_number}. `:""}{player.name}</strong><small>{canGoals?`${player.goals} mål`:""}{canAssists&&detail.enabled.assists?` · ${player.assists} assist`:""}{canCards&&detail.enabled.cards?` · ${player.yellow_cards} gula · ${player.red_cards} röda`:""}</small></div><div className="reporter-player-actions">{canGoals&&<Counter label="Mål" value={player.goals} disabled={locked} minus={()=>void change(player,"goals",-1)} plus={()=>void change(player,"goals",1)}/>}{canAssists&&detail.enabled.assists&&<Counter label="Assist" value={player.assists} disabled={locked} minus={()=>void change(player,"assists",-1)} plus={()=>void change(player,"assists",1)}/>} {canCards&&detail.enabled.cards&&<><Counter label="Gult" value={player.yellow_cards} disabled={locked} minus={()=>void change(player,"yellow_cards",-1)} plus={()=>void change(player,"yellow_cards",1)}/><Counter label="Rött" value={player.red_cards} disabled={locked} minus={()=>void change(player,"red_cards",-1)} plus={()=>void change(player,"red_cards",1)}/></>}</div></article>)}</div>:<div className="reporter-events__empty"><strong>Trupp saknas</strong><span>Lägg in spelarna i lagets trupp för att kunna koppla mål och kort.</span></div>}{canGoals&&team.registered_goals<team.team_score&&<p className="reporter-events__warning">{team.team_score-team.registered_goals} mål saknar spelarkoppling, exempelvis självmål eller okänd målskytt.</p>}</section>)}</div></>}
 </section>;
}

function Counter({label,value,disabled,minus,plus}:{label:string;value:number;disabled:boolean;minus:()=>void;plus:()=>void}){
 return <span className="reporter-counter"><small>{label}</small><button type="button" aria-label={`Minska ${label}`} disabled={disabled||value<=0} onClick={minus}>−</button><strong aria-live="polite">{value}</strong><button type="button" aria-label={`Öka ${label}`} disabled={disabled} onClick={plus}>+</button></span>;
}
