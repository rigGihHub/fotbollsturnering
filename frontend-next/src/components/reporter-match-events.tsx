"use client";

import {useCallback,useEffect,useMemo,useState} from "react";
import {CLIENT_API_BASE} from "../lib/client-api";

const API=CLIENT_API_BASE;
type EventValues={goals:number;assists:number;yellow_cards:number;red_cards:number};
type EventMatch={id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_id:number;away_team_id:number;home_team_name:string;away_team_name:string;home_score:number;away_score:number};
type Player=EventValues&{id:number;name:string;player_number?:number|null};
type Team={side:"home"|"away";team_id:number;team_name:string;team_score:number;players:Player[];registered_goals:number;registered_assists:number};
type Detail={match:{id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;home_team_name:string;away_team_name:string;home_score:number;away_score:number};enabled:{assists:boolean;cards:boolean};teams:Team[]};

async function req<T>(path:string,token:string,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);headers.set("Authorization",`Bearer ${token}`);if(init.body)headers.set("Content-Type","application/json");
 const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});
 const payload=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
 return payload as T;
}
function values(player:Player):EventValues{return {goals:player.goals||0,assists:player.assists||0,yellow_cards:player.yellow_cards||0,red_cards:player.red_cards||0};}
function eventLabel(field:keyof EventValues){return field==="goals"?"mål":field==="assists"?"assist":field==="yellow_cards"?"gult kort":"rött kort";}

export default function ReporterMatchEvents({token,onAuthError}:{token:string;onAuthError?:()=>void}){
 const[matches,setMatches]=useState<EventMatch[]>([]),[matchId,setMatchId]=useState<number|null>(null),[detail,setDetail]=useState<Detail|null>(null);
 const[busyKey,setBusyKey]=useState(""),[error,setError]=useState(""),[message,setMessage]=useState("");
 const handleError=useCallback((err:unknown,fallback:string)=>{const text=err instanceof Error?err.message:fallback;if(/session expired|authentication required/i.test(text))onAuthError?.();setError(text)},[onAuthError]);
 const loadMatches=useCallback(async()=>{try{const payload=await req<{matches:EventMatch[]}>("/api/reporter/reporting/events",token);setMatches(payload.matches||[]);setMatchId(current=>current&&payload.matches.some(m=>m.id===current)?current:(payload.matches[0]?.id??null));setError("")}catch(err){handleError(err,"Matchhändelser kunde inte hämtas.")}},[handleError,token]);
 useEffect(()=>{void loadMatches()},[loadMatches]);
 useEffect(()=>{if(!matchId){setDetail(null);return}let cancelled=false;req<Detail>(`/api/reporter/reporting/matches/${matchId}/events`,token).then(payload=>{if(!cancelled){setDetail(payload);setError("")}}).catch(err=>{if(!cancelled)handleError(err,"Matchen kunde inte hämtas.")});return()=>{cancelled=true}},[handleError,matchId,token]);
 const selected=useMemo(()=>matches.find(match=>match.id===matchId)||null,[matches,matchId]);
 async function change(player:Player,field:keyof EventValues,delta:number){
  if(!detail)return;
  const previous=values(player);const next={...previous,[field]:Math.max(0,previous[field]+delta)};if(next[field]===previous[field])return;
  const key=`${player.id}-${field}`;setBusyKey(key);setError("");setMessage("");
  try{
   const payload=await req<Detail>(`/api/reporter/reporting/matches/${detail.match.id}/events/${player.id}`,token,{method:"PUT",body:JSON.stringify({...next,expected:previous})});
   setDetail(payload);setMessage(`${player.name}: ${eventLabel(field)} uppdaterat.`);
  }catch(err){
   handleError(err,"Händelsen kunde inte sparas.");
   if(matchId)try{setDetail(await req<Detail>(`/api/reporter/reporting/matches/${matchId}/events`,token))}catch{}
  }finally{setBusyKey("")}
 }
 return <section className="admin-panel" id="reporter-events">
  <div className="admin-panel__top"><span>MATCHHÄNDELSER</span><strong>SNABBINMATNING</strong></div>
  <div className="admin-cupinfo__head"><div><h2>Målskyttar, assist & kort</h2><p>Välj en färdigspelad match. Tryck + eller − på spelaren; varje ändring sparas direkt och kontrolleras mot matchresultatet.</p></div><span className="admin-lock">REPORTER</span></div>
  {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:14}}><b>{error?"Fel":"Sparat"}</b> · {error||message}</div>}
  {matches.length?<label style={{display:"grid",gap:6,marginBottom:16}}>Match<select value={matchId??""} onChange={event=>setMatchId(Number(event.target.value))}>{matches.map(match=><option key={match.id} value={match.id}>{match.home_team_name} – {match.away_team_name} · {match.home_score}-{match.away_score}</option>)}</select></label>:<div className="admin-empty"><strong>Inga färdigspelade matcher ännu</strong><span>Spara ett matchresultat först. Då blir målskyttar, assist och kort tillgängliga här.</span></div>}
  {selected&&detail&&<><div className="admin-code-placeholder" style={{marginBottom:14}}><b>{selected.home_team_name} {selected.home_score}–{selected.away_score} {selected.away_team_name}</b> · {selected.stage||"Match"}</div>{detail.teams.map(team=><section key={team.team_id} className="admin-panel" style={{marginBottom:14}}><div className="admin-panel__top"><span>{team.team_name}</span><strong>{team.registered_goals}/{team.team_score} MÅL KOPPLADE</strong></div>{team.players.length?<div className="admin-team-list">{team.players.map(player=><article key={player.id} style={{display:"block"}}><div><strong>{player.player_number!=null?`${player.player_number}. `:""}{player.name}</strong><small>{player.goals} mål{detail.enabled.assists?` · ${player.assists} assist`:""}{detail.enabled.cards?` · ${player.yellow_cards} gula · ${player.red_cards} röda`:""}</small></div><div className="admin-team-actions" style={{marginTop:10,flexWrap:"wrap"}}><Counter label="Mål" value={player.goals} disabled={!!busyKey} minus={()=>void change(player,"goals",-1)} plus={()=>void change(player,"goals",1)}/>{detail.enabled.assists&&<Counter label="Assist" value={player.assists} disabled={!!busyKey} minus={()=>void change(player,"assists",-1)} plus={()=>void change(player,"assists",1)}/>} {detail.enabled.cards&&<><Counter label="Gult" value={player.yellow_cards} disabled={!!busyKey} minus={()=>void change(player,"yellow_cards",-1)} plus={()=>void change(player,"yellow_cards",1)}/><Counter label="Rött" value={player.red_cards} disabled={!!busyKey} minus={()=>void change(player,"red_cards",-1)} plus={()=>void change(player,"red_cards",1)}/></>}</div></article>)}</div>:<div className="admin-empty"><strong>Inga spelare registrerade</strong><span>Cupadministratören behöver lägga in truppen innan individuella händelser kan registreras.</span></div>}{team.registered_goals<team.team_score&&<p><small>{team.team_score-team.registered_goals} mål saknar spelarkoppling, exempelvis självmål eller okänd målskytt.</small></p>}</section>)}</>}
 </section>
}

function Counter({label,value,disabled,minus,plus}:{label:string;value:number;disabled:boolean;minus:()=>void;plus:()=>void}){
 return <span style={{display:"inline-flex",alignItems:"center",gap:6}}><small>{label}</small><button type="button" aria-label={`Minska ${label}`} disabled={disabled||value<=0} onClick={minus}>−</button><strong style={{minWidth:18,textAlign:"center"}}>{value}</strong><button type="button" aria-label={`Öka ${label}`} disabled={disabled} onClick={plus}>+</button></span>;
}
