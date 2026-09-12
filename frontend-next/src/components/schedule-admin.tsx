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
type ProposalPlacement={match_id:number;scheduled_start:string;pitch_number:number};
type ProposalUnresolved={match_id:number;reason:"played_without_schedule"|"locked_without_schedule"|"no_feasible_slot"};
type ScheduleProposal={
  deterministic:boolean;writes_database:boolean;fingerprint:string;match_duration_minutes:number;pitch_break_minutes:number;minimum_team_rest_minutes:number;
  preserved_count:number;candidate_count:number;placed_count:number;unresolved_count:number;
  placements:ProposalPlacement[];unresolved:ProposalUnresolved[];source_match_count:number;window_count:number;
};
type ApplyResult={
  applied:boolean;applied_count:number;fingerprint:string;unresolved_count:number;
  post_apply_conflict_analysis:ConflictAnalysis;schedule:SchedulePayload;
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
function unresolvedLabel(reason:ProposalUnresolved["reason"]){
  if(reason==="locked_without_schedule")return "Matchen är låst utan tid";
  if(reason==="played_without_schedule")return "Spelad match saknar schema";
  return "Ingen regelmässigt möjlig tid hittades";
}

export default function ScheduleAdmin({token,cupId}:{token:string;cupId:number}){
  const[data,setData]=useState<SchedulePayload|null>(null);const[proposal,setProposal]=useState<ScheduleProposal|null>(null);const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");const[message,setMessage]=useState("");const[filter,setFilter]=useState<"all"|"scheduled"|"unscheduled">("all");
  const load=useCallback(async()=>{setBusy(true);setError("");try{setData(await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token));setProposal(null);}catch(err){setError(err instanceof Error?err.message:"Schemat kunde inte hämtas.");}finally{setBusy(false);}},[cupId,token]);
  useEffect(()=>{void load();},[load]);
  const visible=useMemo(()=>{if(!data)return[];if(filter==="scheduled")return data.matches.filter(m=>m.scheduled_start);if(filter==="unscheduled")return data.matches.filter(m=>!m.scheduled_start);return data.matches;},[data,filter]);
  const matchById=useMemo(()=>new Map((data?.matches||[]).map(match=>[match.id,match])),[data]);
  function patchMatch(id:number,patch:Partial<MatchRow>){if(!data)return;setData({...data,matches:data.matches.map(m=>m.id===id?{...m,...patch}:m)});setProposal(null);}
  async function saveMatch(match:MatchRow){setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:match.scheduled_start||null,pitch_number:match.pitch_number??null})},token);setData(saved);setProposal(null);setMessage(`Match ${match.match_no||match.id} har uppdaterats. Konfliktkontrollen är omräknad.`);}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte uppdateras.");}finally{setBusy(false);}}
  async function clearMatch(match:MatchRow){if(!window.confirm(`Ta bort tid och plan för ${match.home_label} – ${match.away_label}?`))return;setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:null,pitch_number:null})},token);setData(saved);setProposal(null);setMessage("Matchen är nu oschemalagd och konfliktkontrollen är omräknad.");}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte göras oschemalagd.");}finally{setBusy(false);}}
  async function createProposal(){setBusy(true);setError("");setMessage("");try{const next=await api<ScheduleProposal>(`/api/admin/cups/${cupId}/schedule/proposal`,{method:"POST"},token);setProposal(next);setMessage("Schemaförslaget är beräknat. Ingenting har skrivits till databasen.");}catch(err){setError(err instanceof Error?err.message:"Schemaförslaget kunde inte beräknas.");}finally{setBusy(false);}}
  async function applyProposal(){
    if(!proposal||proposal.placed_count===0)return;
    const warning=proposal.unresolved_count?` ${proposal.unresolved_count} matcher kan fortfarande behöva lösas manuellt.`:"";
    if(!window.confirm(`Applicera ${proposal.placed_count} granskade schemaplaceringar?${warning} CupNavi kontrollerar att ingenting har ändrats sedan förslaget skapades.`))return;
    setBusy(true);setError("");setMessage("");
    try{
      const result=await api<ApplyResult>(`/api/admin/cups/${cupId}/schedule/proposal/apply`,{method:"POST",body:JSON.stringify({fingerprint:proposal.fingerprint})},token);
      setData(result.schedule);setProposal(null);
      const conflicts=result.post_apply_conflict_analysis;
      setMessage(`${result.applied_count} matcher schemalagda. Slutkontroll: ${conflicts.error_count} fel och ${conflicts.warning_count} varningar.${result.unresolved_count?` ${result.unresolved_count} matcher återstår för manuell hantering.`:""}`);
    }catch(err){
      setProposal(null);
      setError(err instanceof Error?err.message:"Schemaförslaget kunde inte appliceras. Räkna om förslaget och försök igen.");
    }finally{setBusy(false);}
  }
  if(!data)return <section className="admin-panel admin-teams" id="schedule"><div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Schema</h2><p>{error||"Hämtar riktiga matcher…"}</p></section>;
  const analysis=data.conflict_analysis;
  return <section className="admin-panel admin-teams" id="schedule">
    <div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{data.scheduled_count}/{data.match_count} SCHEMALAGDA</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Matchschema</h2><p>Manuell schemaläggning, serverberäknad krockkontroll och deterministiska schemaförslag som alltid granskas innan något sparas.</p></div><span className="admin-lock">LIVE DATA + KROCKKONTROLL</span></div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
    <div className="admin-dashboard-grid" style={{marginBottom:18}}>
      <article className="admin-panel"><strong>{data.match_count}</strong><small>matcher totalt</small></article>
      <article className="admin-panel"><strong>{data.scheduled_count}</strong><small>schemalagda</small></article>
      <article className="admin-panel"><strong>{analysis.conflict_count}</strong><small>{analysis.conflict_count===1?"schemaavvikelse":"schemaavvikelser"}</small></article>
    </div>
    <section className="admin-panel" style={{marginBottom:16}}><div className="admin-panel__top"><span>AUTO / FÖRSLAG</span><strong>GRANSKA → APPLICERA</strong></div><h3>Säkert schemaförslag</h3><p>CupNavi behåller redan schemalagda matcher och försöker placera återstående matcher efter planfönster, matchlängd, planpaus och minsta lagvila. Förslaget får ett fingerprint av exakt den data som användes. Vid applicering bygger servern om förslaget och vägrar skriva om något har ändrats.</p><div className="admin-form-footer"><span>{proposal?`${proposal.placed_count}/${proposal.candidate_count} oschemalagda matcher kunde placeras · ${proposal.unresolved_count} kräver manuell lösning.`:"Skapa först ett förslag. Du kan granska varje placering innan någon databasändring sker."}</span><div className="admin-team-actions"><button type="button" onClick={()=>void createProposal()} disabled={busy||data.unscheduled_count===0}>{busy?"Arbetar…":proposal?"Räkna om":"Skapa schemaförslag"}</button>{proposal&&proposal.placed_count>0&&<button type="button" onClick={()=>void applyProposal()} disabled={busy}>Använd detta schema</button>}</div></div>{proposal&&<div className="admin-team-list" style={{marginTop:16}}>{proposal.placements.map(item=>{const match=matchById.get(item.match_id);return <article key={`proposal-${item.match_id}`}><div><strong>{match?`${match.home_label} – ${match.away_label}`:`Match ${item.match_id}`}</strong><small>Föreslagen tid {item.scheduled_start.replace("T"," ")} · Plan {item.pitch_number}</small></div><strong>FÖRSLAG</strong></article>})}{proposal.unresolved.map(item=>{const match=matchById.get(item.match_id);return <article key={`unresolved-${item.match_id}`}><div><strong>{match?`${match.home_label} – ${match.away_label}`:`Match ${item.match_id}`}</strong><small>{unresolvedLabel(item.reason)}</small></div><strong>MANUELLT</strong></article>})}</div>}</section>
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
    <div className="admin-form-footer"><span>Förslag appliceras endast om serverns aktuella data fortfarande matchar det granskade fingerprintet. Efter skrivning körs konfliktkontrollen igen.</span><button type="button" onClick={()=>void load()} disabled={busy}>{busy?"Hämtar…":"Uppdatera schema"}</button></div>
  </section>;
}
