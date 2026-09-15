"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE=CLIENT_API_BASE;

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
  schedule_dirty:boolean; is_published:boolean; arrangement_type?:string; conflict_analysis:ConflictAnalysis;
};
type ProposalPlacement={match_id:number;scheduled_start:string;pitch_number:number};
type ProposalUnresolved={match_id:number;reason:"played_without_schedule"|"locked_without_schedule"|"no_feasible_slot"|"round_order_blocked"};
type ProposalQuality={
  strategy:string;round_order_enforced:boolean;plan_change_count:number;minimum_observed_rest_minutes:number|null;
  average_observed_rest_minutes:number|null;schedule_span_minutes:number;round_order_violation_count:number;
};
type ScheduleProposal={
  deterministic:boolean;writes_database:boolean;fingerprint:string;match_duration_minutes:number;pitch_break_minutes:number;minimum_team_rest_minutes:number;
  preserved_count:number;candidate_count:number;placed_count:number;unresolved_count:number;
  placements:ProposalPlacement[];unresolved:ProposalUnresolved[];source_match_count:number;window_count:number;quality:ProposalQuality;
};
type ApplyResult={
  applied:boolean;applied_count:number;fingerprint:string;unresolved_count:number;
  post_apply_conflict_analysis:ConflictAnalysis;schedule:SchedulePayload;
};
type ImportSummary={available:boolean;source_name?:string|null;expected?:{matches?:number};actual?:{matches?:number}};
type MatchcampPair={match_no:number;home_team_id:number;home_name:string;away_team_id:number;away_name:string};
type MatchcampProposal={writes_database:boolean;fingerprint:string;matches_per_team:number;team_count:number;match_count:number;minimum_matches:number;maximum_matches:number;balanced:boolean;pairs:MatchcampPair[]};

async function api<T>(path:string,options:RequestInit,token:string):Promise<T>{
  const headers=new Headers(options.headers||{});if(options.body)headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response=await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
  return payload as T;
}

function localInput(value?:string|null){return value?value.slice(0,16):"";}
function minutesLabel(value:number){const hours=Math.floor(value/60);const minutes=value%60;return hours?`${hours} h ${minutes} min`:`${minutes} min`;}
function conflictMatches(conflict:ScheduleConflict){
  const rows=conflict.matches||(conflict.match?[conflict.match]:[]);
  return rows.map(row=>`${row.match_no?`Match ${row.match_no}`:`Match ${row.match_id}`}${row.home_label&&row.away_label?` · ${row.home_label} – ${row.away_label}`:""}`).join(" / ");
}
function unresolvedLabel(reason:ProposalUnresolved["reason"]){
  if(reason==="locked_without_schedule")return "Matchen är låst utan tid";
  if(reason==="played_without_schedule")return "Spelad match saknar schema";
  if(reason==="round_order_blocked")return "Rundordningen blockerar alla återstående tider";
  return "Ingen regelmässigt möjlig tid hittades";
}

export default function ScheduleAdmin({token,cupId}:{token:string;cupId:number}){
  const[data,setData]=useState<SchedulePayload|null>(null);const[proposal,setProposal]=useState<ScheduleProposal|null>(null);const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");const[message,setMessage]=useState("");const[filter,setFilter]=useState<"all"|"scheduled"|"unscheduled">("all");const[importSummary,setImportSummary]=useState<ImportSummary|null>(null);
  const[matchesPerTeam,setMatchesPerTeam]=useState(4);const[matchcampProposal,setMatchcampProposal]=useState<MatchcampProposal|null>(null);
  const load=useCallback(async()=>{setBusy(true);setError("");try{const schedule=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token);setData(schedule);setProposal(null);if(schedule.match_count===0){try{setImportSummary(await api<ImportSummary>(`/api/admin/cups/${cupId}/import/summary`,{},token));}catch{setImportSummary(null);}}else setImportSummary(null);}catch(err){setError(err instanceof Error?err.message:"Schemat kunde inte hämtas.");}finally{setBusy(false);}},[cupId,token]);
  useEffect(()=>{void load();},[load]);
  const visible=useMemo(()=>{if(!data)return[];if(filter==="scheduled")return data.matches.filter(m=>m.scheduled_start);if(filter==="unscheduled")return data.matches.filter(m=>!m.scheduled_start);return data.matches;},[data,filter]);
  const matchById=useMemo(()=>new Map((data?.matches||[]).map(match=>[match.id,match])),[data]);
  function patchMatch(id:number,patch:Partial<MatchRow>){if(!data)return;setData({...data,matches:data.matches.map(m=>m.id===id?{...m,...patch}:m)});setProposal(null);}
  async function saveMatch(match:MatchRow){setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:match.scheduled_start||null,pitch_number:match.pitch_number??null})},token);setData(saved);setProposal(null);setMessage(`Match ${match.match_no||match.id} har uppdaterats. Konfliktkontrollen är omräknad.`);}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte uppdateras.");}finally{setBusy(false);}}
  async function clearMatch(match:MatchRow){if(!window.confirm(`Ta bort tid och plan för ${match.home_label} – ${match.away_label}?`))return;setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:null,pitch_number:null})},token);setData(saved);setProposal(null);setMessage("Matchen är nu oschemalagd och konfliktkontrollen är omräknad.");}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte göras oschemalagd.");}finally{setBusy(false);}}
  async function createProposal(){setBusy(true);setError("");setMessage("");try{const next=await api<ScheduleProposal>(`/api/admin/cups/${cupId}/schedule/proposal`,{method:"POST"},token);setProposal(next);setMessage("Schemaförslaget är beräknat. Ingenting har skrivits till databasen.");}catch(err){setError(err instanceof Error?err.message:"Schemaförslaget kunde inte beräknas.");}finally{setBusy(false);}}
  async function restoreImportedMatches(){setBusy(true);setError("");setMessage("");try{const result=await api<{restored_count:number}>(`/api/admin/cups/${cupId}/import/restore-matches`,{method:"POST"},token);await load();setMessage(`${result.restored_count} matcher från den första importen har återställts.`);}catch(err){setError(err instanceof Error?err.message:"Matchprogrammet kunde inte återställas.");setBusy(false);}}
  async function previewMatchcamp(){setBusy(true);setError("");setMessage("");setMatchcampProposal(null);try{const result=await api<MatchcampProposal>(`/api/admin/cups/${cupId}/matchcamp/pairings/preview`,{method:"POST",body:JSON.stringify({matches_per_team:matchesPerTeam})},token);setMatchcampProposal(result);setMessage("Matchförslaget är klart. Ingenting har sparats ännu.");}catch(err){setError(err instanceof Error?err.message:"Matchförslaget kunde inte skapas.");}finally{setBusy(false);}}
  async function applyMatchcamp(){if(!matchcampProposal)return;setBusy(true);setError("");setMessage("");try{await api<{created_count:number}>(`/api/admin/cups/${cupId}/matchcamp/pairings/apply`,{method:"POST",body:JSON.stringify({matches_per_team:matchesPerTeam,fingerprint:matchcampProposal.fingerprint})},token);setMatchcampProposal(null);await load();setMessage("Matchmötena är sparade. Skapa nu ett schemaförslag för tider och planer.");}catch(err){setError(err instanceof Error?err.message:"Matchmötena kunde inte sparas.");setBusy(false);}}
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
  if(!data)return <section className="admin-panel admin-teams" id="schedule"><div className="admin-panel__top"><span>GUIDE / SCHEMA</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Schema</h2><p>{error||"Hämtar riktiga matcher…"}</p></section>;
  const analysis=data.conflict_analysis;
  return <section className="admin-panel admin-teams" id="schedule">
    <div className="admin-panel__top"><span>GUIDE / SCHEMA</span><strong>{data.scheduled_count}/{data.match_count} SCHEMALAGDA</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Skapa matchschemat</h2><p>CupNavi placerar matcherna åt dig utifrån planer, öppettider och viloregler. Du granskar alltid resultatet innan det sparas.</p></div><span className="admin-lock">GRANSKA → SPARA</span></div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
    {data.match_count===0&&data.arrangement_type==="matchcamp"?<section className="matchcamp-builder">
      <div className="admin-panel__top"><span>1 · SKAPA MÖTENA</span><strong>INGET SPARAS ÄN</strong></div>
      <h3>Hur många matcher ska varje lag få?</h3><p>CupNavi skapar unika möten. Tider och planer läggs på först i nästa kontrollsteg.</p>
      <div className="matchcamp-builder__controls"><label>Matcher per lag<input type="number" min={1} max={12} value={matchesPerTeam} onChange={e=>{setMatchesPerTeam(Number(e.target.value));setMatchcampProposal(null);}}/></label><button type="button" disabled={busy} onClick={()=>void previewMatchcamp()}>{busy?"Räknar…":"Skapa matchförslag"}</button></div>
      {matchcampProposal&&<><div className="matchcamp-builder__summary"><strong>{matchcampProposal.match_count} matcher</strong><span>{matchcampProposal.minimum_matches===matchcampProposal.maximum_matches?`${matchcampProposal.minimum_matches} per lag`:`${matchcampProposal.minimum_matches}–${matchcampProposal.maximum_matches} per lag`}</span>{!matchcampProposal.balanced&&<small>Udda antal lag gör att ett lag vilar varje omgång.</small>}</div><div className="admin-team-list">{matchcampProposal.pairs.map(pair=><article key={pair.match_no}><strong>Match {pair.match_no}</strong><span>{pair.home_name} – {pair.away_name}</span></article>)}</div><div className="admin-form-footer"><span>Granska alla möten innan de skapas.</span><button type="button" disabled={busy} onClick={()=>void applyMatchcamp()}>Godkänn och skapa matcherna</button></div></>}
    </section>:data.match_count===0?<section className="schedule-empty-guide">
      <span className="schedule-empty-guide__number">1</span>
      {Number(importSummary?.expected?.matches||0)>0?<><div><p className="kicker">ORIGINALIMPORT HITTAD</p><h3>Återställ det redan importerade schemat</h3><p>Den första importen innehöll {importSummary?.expected?.matches} matcher, men de saknas i schemat. Återställ dem från det sparade underlaget – du behöver inte ladda upp något igen.</p></div><div className="schedule-empty-guide__actions"><button className="is-primary" type="button" disabled={busy} onClick={()=>void restoreImportedMatches()}>{busy?"Återställer…":`Återställ ${importSummary?.expected?.matches} matcher`}</button><a href="#groups">Kontrollera grupper</a></div></>:<><div><p className="kicker">INGA MATCHER HITTADE</p><h3>Matchprogram saknas</h3><p>Den första importen innehöll inget användbart matchprogram. Kontrollera grupperna och öppna endast Import om du verkligen behöver lägga in ett nytt underlag.</p></div><div className="schedule-empty-guide__actions"><a className="is-primary" href="#groups">Kontrollera grupper</a><a href="#import">Öppna Import</a></div></>}
    </section>:<>
    <div className="admin-dashboard-grid" style={{marginBottom:18}}>
      <article className="admin-panel"><strong>{data.match_count}</strong><small>matcher totalt</small></article>
      <article className="admin-panel"><strong>{data.scheduled_count}</strong><small>schemalagda</small></article>
      <article className="admin-panel"><strong>{analysis.conflict_count}</strong><small>{analysis.conflict_count===1?"schemaavvikelse":"schemaavvikelser"}</small></article>
    </div>
    <section className="admin-panel schedule-proposal" style={{marginBottom:16}}><div className="admin-panel__top"><span>1 · LÅT CUPNAVI PLANERA</span><strong>INGET SPARAS ÄN</strong></div><h3>{data.unscheduled_count?`Placera ${data.unscheduled_count} oschemalagda matcher`:"Alla matcher har redan en tid"}</h3><p>CupNavi räknar fram ett förslag utifrån planernas öppettider, matchlängd, pauser och lagvila. Befintliga matchtider behålls.</p><div className="admin-form-footer"><span>{proposal?`${proposal.placed_count} matcher fick en tid${proposal.unresolved_count?` · ${proposal.unresolved_count} behöver lösas manuellt`:""}. Granska listan innan du sparar.`:data.unscheduled_count?"Tryck på knappen för att skapa ett granskningsbart förslag.":"Du kan kontrollera eller justera matcherna nedan."}</span><div className="admin-team-actions"><button type="button" onClick={()=>void createProposal()} disabled={busy||data.unscheduled_count===0}>{busy?"Räknar…":proposal?"Räkna om förslaget":"Skapa schemaförslag"}</button>{proposal&&proposal.placed_count>0&&<button type="button" onClick={()=>void applyProposal()} disabled={busy}>Spara det granskade schemat</button>}</div></div>{proposal&&<><h3 className="schedule-review-title">2 · Granska förslaget</h3><div className="admin-dashboard-grid" style={{marginTop:16}}><article className="admin-panel"><strong>{proposal.placed_count}</strong><small>matcher placerade</small></article><article className="admin-panel"><strong>{proposal.unresolved_count}</strong><small>behöver hjälp</small></article><article className="admin-panel"><strong>{proposal.quality.minimum_observed_rest_minutes??"–"}</strong><small>minsta lagvila, min</small></article></div><div className="admin-team-list" style={{marginTop:16}}>{proposal.placements.map(item=>{const match=matchById.get(item.match_id);return <article key={`proposal-${item.match_id}`}><div><strong>{match?`${match.home_label} – ${match.away_label}`:`Match ${item.match_id}`}</strong><small>{item.scheduled_start.replace("T"," ")} · Plan {item.pitch_number}</small></div><strong>FÖRSLAG</strong></article>})}{proposal.unresolved.map(item=>{const match=matchById.get(item.match_id);return <article key={`unresolved-${item.match_id}`}><div><strong>{match?`${match.home_label} – ${match.away_label}`:`Match ${item.match_id}`}</strong><small>{unresolvedLabel(item.reason)}</small></div><strong>MANUELLT</strong></article>})}</div></>}</section>
    {analysis.ok?<div className="admin-code-placeholder" style={{marginBottom:16}}><b>Ingen krock hittad</b> · {analysis.match_duration_minutes} min match · {analysis.pitch_break_minutes} min planpaus · minst {analysis.minimum_team_rest_minutes} min lagvila.</div>:<section className="admin-panel" style={{marginBottom:16}}><div className="admin-panel__top"><span>SCHEMAKONTROLL</span><strong>{analysis.error_count} FEL · {analysis.warning_count} VARNINGAR</strong></div><h3>Åtgärda innan publicering</h3><div className="admin-team-list">{analysis.conflicts.map((conflict,index)=><article key={`${conflict.type}-${conflict.match_ids.join("-")}-${index}`}><div><strong>{conflict.severity==="error"?"STOPP":"VARNING"} · {conflict.message}</strong><small>{conflictMatches(conflict)}</small></div></article>)}</div></section>}
    {data.schedule_dirty&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>Kontroll krävs</b> · schemat är ändrat sedan senaste publicering. Konfliktlistan ovan räknas från aktuell serverdata.</div>}
    <div className="admin-team-actions" style={{marginBottom:16}}><button type="button" onClick={()=>setFilter("all")} disabled={filter==="all"}>Alla</button><button type="button" onClick={()=>setFilter("scheduled")} disabled={filter==="scheduled"}>Schemalagda</button><button type="button" onClick={()=>setFilter("unscheduled")} disabled={filter==="unscheduled"}>Oschemalagda</button></div>
    <div className="admin-team-list">
      {visible.length?visible.map(match=><article key={match.id} style={{alignItems:"end"}}>
        <div style={{flex:1,minWidth:220}}><strong>{match.home_label} – {match.away_label}</strong><small>{match.stage}{match.group_name?` · ${match.group_name}`:""}{match.match_no?` · match ${match.match_no}`:""}{match.played?" · SPELAD":match.schedule_locked?" · LÅST":""}</small></div>
        <label style={{minWidth:190}}>Tid<input type="datetime-local" disabled={busy||match.played||match.schedule_locked} value={localInput(match.scheduled_start)} onChange={e=>patchMatch(match.id,{scheduled_start:e.target.value||null})}/></label>
        <label style={{minWidth:110}}>Plan<select disabled={busy||match.played||match.schedule_locked} value={match.pitch_number??""} onChange={e=>patchMatch(match.id,{pitch_number:e.target.value?Number(e.target.value):null})}><option value="">Ingen</option>{Array.from({length:data.pitch_count},(_,i)=>i+1).map(n=><option key={n} value={n}>Plan {n}</option>)}</select></label>
        <div className="admin-team-actions"><button type="button" disabled={busy||match.played||match.schedule_locked||!match.scheduled_start||!match.pitch_number} onClick={()=>saveMatch(match)}>Spara</button>{match.scheduled_start&&<button type="button" disabled={busy||match.played||match.schedule_locked} onClick={()=>clearMatch(match)}>Gör oschemalagd</button>}</div>
      </article>):<div className="admin-empty"><strong>Inga matcher i den här listan</strong><span>Välj ett annat filter ovan.</span></div>}
    </div>
    <div className="admin-form-footer"><span>CupNavi kontrollerar automatiskt krockar och lagvila varje gång schemat sparas.</span><button type="button" onClick={()=>void load()} disabled={busy}>{busy?"Hämtar…":"Kontrollera schemat igen"}</button></div>
    </>}
  </section>;
}
