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
 const h=new Headers(init.headers);h.set("Authorization",`Bearer ${token}`);if(init.body)h.set("Content-Type","application/json");
 const r=await fetch(`${API}${path}`,{...init,headers:h,cache:"no-store"});const p=await r.json().catch(()=>null);
 if(!r.ok)throw new Error(p?.detail||`API-fel ${r.status}`);return p as T;
}
const zeros:EventValues={goals:0,assists:0,yellow_cards:0,red_cards:0};
function values(player:Player):EventValues{return {goals:player.goals||0,assists:player.assists||0,yellow_cards:player.yellow_cards||0,red_cards:player.red_cards||0};}

export default function MatchEventsAdmin({token,cupId}:{token:string;cupId:number}){
 const[matches,setMatches]=useState<EventMatch[]>([]),[matchId,setMatchId]=useState<number|null>(null),[detail,setDetail]=useState<Detail|null>(null);
 const[busyKey,setBusyKey]=useState(""),[error,setError]=useState(""),[message,setMessage]=useState("");
 const loadMatches=useCallback(async()=>{try{const p=await req<{matches:EventMatch[]}>(`/api/admin/cups/${cupId}/reporting/events`,token);setMatches(p.matches||[]);setMatchId(current=>current&&p.matches.some(m=>m.id===current)?current:(p.matches[0]?.id??null));setError("")}catch(e){setError(e instanceof Error?e.message:"Matchhändelser kunde inte hämtas")}},[cupId,token]);
 useEffect(()=>{void loadMatches()},[loadMatches]);
 useEffect(()=>{if(!matchId){setDetail(null);return}let cancelled=false;req<Detail>(`/api/admin/cups/${cupId}/reporting/matches/${matchId}/events`,token).then(p=>{if(!cancelled){setDetail(p);setError("")}}).catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:"Matchen kunde inte hämtas")});return()=>{cancelled=true}},[cupId,matchId,token]);
 const selected=useMemo(()=>matches.find(m=>m.id===matchId)||null,[matches,matchId]);
 async function change(team:Team,player:Player,field:keyof EventValues,delta:number){
   const previous=values(player);const next={...previous,[field]:Math.max(0,previous[field]+delta)};if(next[field]===previous[field])return;
   const key=`${player.id}-${field}`;setBusyKey(key);setError("");setMessage("");
   try{const p=await req<Detail>(`/api/admin/cups/${cupId}/reporting/matches/${detail?.match.id}/events/${player.id}`,token,{method:"PUT",body:JSON.stringify({...next,expected:previous})});setDetail(p);setMessage(`${player.name}: ${field==="goals"?"mål":field==="assists"?"assist":field==="yellow_cards"?"gult kort":"rött kort"} uppdaterat.`)}catch(e){setError(e instanceof Error?e.message:"Händelsen kunde inte sparas");if(matchId)try{setDetail(await req<Detail>(`/api/admin/cups/${cupId}/reporting/matches/${matchId}/events`,token))}catch{}}finally{setBusyKey("")}
 }
 return <section className="admin-panel" id="match-events">
   <div className="admin-panel__top"><span>11B / MATCHHÄNDELSER</span><strong>MOBIL SNABBINMATNING</strong></div>
   <div className="admin-cupinfo__head"><div><h2>Målskyttar, assist & kort</h2><p>Välj en färdigspelad match och tryck +/− direkt på spelaren. Varje ändring sparas serververifierat med konfliktkontroll.</p></div><span className="admin-lock">LIVE DATA</span></div>
   {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:14}}><b>{error?"Fel":"Sparat"}</b> · {error||message}</div>}
   {matches.length?<label style={{display:"grid",gap:6,marginBottom:16}}>Match<select value={matchId??""} onChange={e=>setMatchId(Number(e.target.value))}>{matches.map(m=><option key={m.id} value={m.id}>{m.home_team_name} – {m.away_team_name} · {m.home_score}-{m.away_score}</option>)}</select></label>:<div className="admin-empty"><strong>Inga färdigspelade matcher ännu</strong><span>Registrera ett resultat först.</span></div>}
   {selected&&detail&&<><div className="admin-code-placeholder" style={{marginBottom:14}}><b>{selected.home_team_name} {selected.home_score}–{selected.away_score} {selected.away_team_name}</b> · {selected.stage||"Match"}</div>{detail.teams.map(team=><section key={team.team_id} className="admin-panel" style={{marginBottom:14}}><div className="admin-panel__top"><span>{team.team_name}</span><strong>{team.registered_goals}/{team.team_score} MÅL KOPPLADE</strong></div>{team.players.length?<div className="admin-team-list">{team.players.map(player=><article key={player.id} style={{display:"block"}}><div style={{display:"flex",justifyContent:"space-between",gap:10,alignItems:"center"}}><div><strong>{player.player_number!=null?`${player.player_number}. `:""}{player.name}</strong><small>{player.goals} mål{detail.enabled.assists?` · ${player.assists} assist`:""}{detail.enabled.cards?` · ${player.yellow_cards} gula · ${player.red_cards} röda`:""}</small></div></div><div className="admin-team-actions" style={{marginTop:10,flexWrap:"wrap"}}><Counter label="Mål" value={player.goals} disabled={!!busyKey} minus={()=>void change(team,player,"goals",-1)} plus={()=>void change(team,player,"goals",1)}/>{detail.enabled.assists&&<Counter label="Assist" value={player.assists} disabled={!!busyKey} minus={()=>void change(team,player,"assists",-1)} plus={()=>void change(team,player,"assists",1)}/>} {detail.enabled.cards&&<><Counter label="Gult" value={player.yellow_cards} disabled={!!busyKey} minus={()=>void change(team,player,"yellow_cards",-1)} plus={()=>void change(team,player,"yellow_cards",1)}/><Counter label="Rött" value={player.red_cards} disabled={!!busyKey} minus={()=>void change(team,player,"red_cards",-1)} plus={()=>void change(team,player,"red_cards",1)}/></>}</div></article>)}</div>:<div className="admin-empty"><strong>Inga spelare registrerade</strong><span>Lägg in truppen innan individuella matchhändelser kan kopplas.</span></div>}{team.registered_goals<team.team_score&&<p><small>{team.team_score-team.registered_goals} mål saknar spelarkoppling, exempelvis självmål eller okänd målskytt.</small></p>}</section>)}</>}
 </section>
}

function Counter({label,value,disabled,minus,plus}:{label:string;value:number;disabled:boolean;minus:()=>void;plus:()=>void}){
 return <span style={{display:"inline-flex",alignItems:"center",gap:6}}><small>{label}</small><button type="button" aria-label={`Minska ${label}`} disabled={disabled||value<=0} onClick={minus}>−</button><strong style={{minWidth:18,textAlign:"center"}}>{value}</strong><button type="button" aria-label={`Öka ${label}`} disabled={disabled} onClick={plus}>+</button></span>
}
