"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE=(process.env.NEXT_PUBLIC_CUPNAVI_API_BASE||"http://localhost:8000").replace(/\/$/,"");

type MatchRow={
  id:number; group_id?:number|null; group_name?:string|null; stage:string; match_no?:number|null; round_no?:number|null;
  home_source?:string|null; away_source?:string|null; home_label:string; away_label:string;
  scheduled_start?:string|null; pitch_number?:number|null; schedule_locked:boolean; schedule_published:boolean; played:boolean;
};
type ConflictMatch={match_id:number;match_no?:number|null;home_label?:string|null;away_label?:string|null;scheduled_start?:string|null;pitch_number?:number|null};
type ScheduleConflict={
  type:"invalid_start"|"pitch_overlap"|"team_overlap"|"insufficient_rest";severity:"error"|"warning";
  match_ids:number[];message:string;pitch_number?:number;team_id?:number;overlap_minutes?:number;rest_minutes?:number;
  required_rest_minutes?:number;matches?:ConflictMatch[];match?:ConflictMatch;
};
type ConflictAnalysis={
  ok:boolean;conflict_count:number;error_count:number;warning_count:number;match_duration_minutes:number;
  pitch_break_minutes:number;minimum_team_rest_minutes:number;conflicts:ScheduleConflict[];
};
type SchedulePayload={
  matches:MatchRow[]; match_count:number; scheduled_count:number; unscheduled_count:number; pitch_count:number;
  first_match_time:string; latest_kickoff_time:string; start_date?:string|null; end_date?:string|null;
  schedule_dirty:boolean; is_published:boolean; conflict_analysis:ConflictAnalysis;
};

async function api<T>(path:string,options:RequestInit,token:string):Promise<T>{
  const headers=new Headers(options.headers||{});if(options.body)headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response=await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
  return payload as T;
}

function localInput(value?:string|null){return value?value.slice(0,16):"";}
function conflictMatches(conflict:ScheduleConflict){
  const rows=conflict.matches||(conflict.match?[conflict.match]:[]);
  return rows.map(row=>`${row.match_no?`Match ${row.match_no}`:`Match ${row.match_id}`}${row.home_label&&row.away_label?` · ${row.home_label} – ${row.away_label}`:""}`).join(" / ");
}

export default function ScheduleAdmin({token,cupId}:{token:string;cupId:number}){
  const[data,setData]=useState<SchedulePayload|null>(null);const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");const[message,setMessage]=useState("");const[filter,setFilter]=useState<"all"|"scheduled"|"unscheduled">("all");
  const load=useCallback(async()=>{setBusy(true);setError("");try{setData(await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token));}catch(err){setError(err instanceof Error?err.message:"Schemat kunde inte hämtas.");}finally{setBusy(false);}},[cupId,token]);
  useEffect(()=>{void load();},[load]);
  const visible=useMemo(()=>{if(!data)return[];if(filter==="scheduled")return data.matches.filter(m=>m.scheduled_start);if(filter==="unscheduled")return data.matches.filter(m=>!m.scheduled_start);return data.matches;},[data,filter]);
  function patchMatch(id:number,patch:Partial<MatchRow>){if(!data)return;setData({...data,matches:data.matches.map(m=>m.id===id?{...m,...patch}:m)});}
  async function saveMatch(match:MatchRow){setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:match.scheduled_start||null,pitch_number:match.pitch_number??null})},token);setData(saved);setMessage(`Match ${match.match_no||match.id} har uppdaterats. Konfliktkontrollen är omräknad.`);}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte uppdateras.");}finally{setBusy(false);}}
  async function clearMatch(match:MatchRow){if(!window.confirm(`Ta bort tid och plan för ${match.home_label} – ${match.away_label}?`))return;setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:null,pitch_number:null})},token);setData(saved);setMessage("Matchen är nu oschemalagd och konfliktkontrollen är omräknad.");}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte göras oschemalagd.");}finally{setBusy(false);}}
  if(!data)return <section className="admin-panel admin-teams" id="schedule"><div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Schema</h2><p>{error||"Hämtar riktiga matcher…"}</p></section>;
  const analysis=data.conflict_analysis;
  return <section className="admin-panel admin-teams" id="schedule">
    <div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{data.scheduled_count}/{data.match_count} SCHEMALAGDA</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Matchschema</h2><p>Manuell schemaläggning med serverberäknad kontroll av planbokningar, samtidiga lagmatcher och lagvila.</p></div><span className="admin-lock">LIVE DATA + KROCKKONTROLL</span></div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
    <div className="admin-dashboard-grid" style={{marginBottom:18}}>
      <article className="admin-panel"><strong>{data.match_count}</strong><small>matcher totalt</small></article>
      <article className="admin-panel"><strong>{data.scheduled_count}</strong><small>schemalagda</small></article>
      <article className="admin-panel"><strong>{analysis.conflict_count}</strong><small>{analysis.conflict_count===1?"schemaavvikelse":"schemaavvikelser"}</small></article>
    </div>
    {analysis.ok?<div className="admin-code-placeholder" style={{marginBottom:16}}><b>Ingen krock hittad</b> · {analysis.match_duration_minutes} min match · {analysis.pitch_break_minutes} min planpaus · minst {analysis.minimum_team_rest_minutes} min lagvila.</div>:<section className="admin-panel" style={{marginBottom:16}}><div className="admin-panel__top"><span>SCHEMAKONTROLL</span><strong>{analysis.error_count} FEL · {analysis.warning_count} VARNINGAR</strong></div><h3>Åtgärda innan publicering</h3><div className="admin-team-list">{analysis.conflicts.map((conflict,index)=><article key={`${conflict.type}-${conflict.match_ids.join("-")}-${index}`}><div><strong>{conflict.severity==="error"?"STOPP":"VARNING"} · {conflict.message}</strong><small>{conflictMatches(conflict)}</small></div></article>)}</div></section>}
    {data.schedule_dirty&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>Kontroll krävs</b> · schemat är ändrat sedan senaste publicering. Konfliktlistan ovan räknas från aktuell serverdata.</div>}
    <div className="admin-team-actions" style={{marginBottom:16}}><button type="button" onClick={()=>setFilter("all")} disabled={filter==="all"}>Alla</button><button type="button" onClick={()=>setFilter("scheduled")} disabled={filter==="scheduled"}>Schemalagda</button><button type="button" onClick={()=>setFilter("unscheduled")} disabled={filter==="unscheduled"}>Oschemalagda</button></div>
    <div className="admin-team-list">
      {visible.length?visible.map(match=><article key={match.id} style={{alignItems:"end"}}>
        <div style={{flex:1,minWidth:220}}><strong>{match.home_label} – {match.away_label}</strong><small>{match.stage}{match.group_name?` · ${match.group_name}`:""}{match.match_no?` · match ${match.match_no}`:""}{match.played?" · SPELAD":match.schedule_locked?" · LÅST":""}</small></div>
        <label style={{minWidth:190}}>Tid<input type="datetime-local" disabled={busy||match.played||match.schedule_locked} value={localInput(match.scheduled_start)} onChange={e=>patchMatch(match.id,{scheduled_start:e.target.value||null})}/></label>
        <label style={{minWidth:110}}>Plan<select disabled={busy||match.played||match.schedule_locked} value={match.pitch_number??""} onChange={e=>patchMatch(match.id,{pitch_number:e.target.value?Number(e.target.value):null})}><option value="">Ingen</option>{Array.from({length:data.pitch_count},(_,i)=>i+1).map(n=><option key={n} value={n}>Plan {n}</option>)}</select></label>
        <div className="admin-team-actions"><button type="button" disabled={busy||match.played||match.schedule_locked||!match.scheduled_start||!match.pitch_number} onClick={()=>saveMatch(match)}>Spara</button>{match.scheduled_start&&<button type="button" disabled={busy||match.played||match.schedule_locked} onClick={()=>clearMatch(match)}>Gör oschemalagd</button>}</div>
      </article>):<div className="admin-empty"><strong>Inga matcher i filtret</strong><span>Byt filter eller skapa gruppmatcher i det avancerade schemaflödet.</span></div>}
    </div>
    <div className="admin-form-footer"><span>Konfliktkontrollen är deterministisk och flyttar aldrig matcher automatiskt. Nästa schemaetapp kan använda samma motor för att skapa säkra schemaförslag.</span><button type="button" onClick={()=>void load()} disabled={busy}>{busy?"Hämtar…":"Uppdatera schema"}</button></div>
  </section>;
}
