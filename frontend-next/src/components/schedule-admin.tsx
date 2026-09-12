"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE=(process.env.NEXT_PUBLIC_CUPNAVI_API_BASE||"http://localhost:8000").replace(/\/$/,"");

type MatchRow={
  id:number; group_id?:number|null; group_name?:string|null; stage:string; match_no?:number|null; round_no?:number|null;
  home_source?:string|null; away_source?:string|null; home_label:string; away_label:string;
  scheduled_start?:string|null; pitch_number?:number|null; schedule_locked:boolean; schedule_published:boolean; played:boolean;
};
type SchedulePayload={
  matches:MatchRow[]; match_count:number; scheduled_count:number; unscheduled_count:number; pitch_count:number;
  first_match_time:string; latest_kickoff_time:string; start_date?:string|null; end_date?:string|null;
  schedule_dirty:boolean; is_published:boolean;
};
type PreviewUpdate={id:number;scheduled_start:string;pitch_number:number;referee_id?:number|null;stage?:string|null;home_source?:string|null;away_source?:string|null};
type GenerationPreview={engine:string;updates:PreviewUpdate[];unresolved_match_ids:number[];unresolved_count:number;scheduled_count:number;preserved_count:number;safe_to_apply:boolean;applied?:boolean;applied_count?:number;partial?:boolean};

async function api<T>(path:string,options:RequestInit,token:string):Promise<T>{
  const headers=new Headers(options.headers||{});if(options.body)headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response=await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
  return payload as T;
}

function localInput(value?:string|null){return value?value.slice(0,16):"";}
function shortTime(value:string){const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleString("sv-SE",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});}

export default function ScheduleAdmin({token,cupId}:{token:string;cupId:number}){
  const[data,setData]=useState<SchedulePayload|null>(null);const[preview,setPreview]=useState<GenerationPreview|null>(null);const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");const[message,setMessage]=useState("");const[filter,setFilter]=useState<"all"|"scheduled"|"unscheduled">("all");
  const load=useCallback(async()=>{setBusy(true);setError("");try{setData(await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token));setPreview(null);}catch(err){setError(err instanceof Error?err.message:"Schemat kunde inte hämtas.");}finally{setBusy(false);}},[cupId,token]);
  useEffect(()=>{void load();},[load]);
  const visible=useMemo(()=>{if(!data)return[];if(filter==="scheduled")return data.matches.filter(m=>m.scheduled_start);if(filter==="unscheduled")return data.matches.filter(m=>!m.scheduled_start);return data.matches;},[data,filter]);
  const matchById=useMemo(()=>new Map((data?.matches||[]).map(match=>[match.id,match])),[data]);
  function patchMatch(id:number,patch:Partial<MatchRow>){if(!data)return;setData({...data,matches:data.matches.map(m=>m.id===id?{...m,...patch}:m)});setPreview(null);}
  async function saveMatch(match:MatchRow){setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:match.scheduled_start||null,pitch_number:match.pitch_number??null})},token);setData(saved);setPreview(null);setMessage(`Match ${match.match_no||match.id} har uppdaterats. Publiceringen är avstängd tills schemat kontrollerats.`);}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte uppdateras.");}finally{setBusy(false);}}
  async function clearMatch(match:MatchRow){if(!window.confirm(`Ta bort tid och plan för ${match.home_label} – ${match.away_label}?`))return;setBusy(true);setError("");setMessage("");try{const saved=await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule/matches/${match.id}`,{method:"PUT",body:JSON.stringify({scheduled_start:null,pitch_number:null})},token);setData(saved);setPreview(null);setMessage("Matchen är nu oschemalagd.");}catch(err){setError(err instanceof Error?err.message:"Matchen kunde inte göras oschemalagd.");}finally{setBusy(false);}}
  async function previewSchedule(){setBusy(true);setError("");setMessage("");try{const result=await api<GenerationPreview>(`/api/admin/cups/${cupId}/schedule/generation-preview`,{},token);setPreview(result);setMessage(result.safe_to_apply?`Förslag klart: ${result.scheduled_count} matcher kan schemaläggas utan att befintliga tider skrivs över.`:`Förslag skapat, men ${result.unresolved_count} matcher kräver fortsatt hantering innan ett komplett schema kan sparas.`);}catch(err){setPreview(null);setError(err instanceof Error?err.message:"Autoschemat kunde inte förhandsgranskas.");}finally{setBusy(false);}}
  async function applySchedule(){if(!preview?.safe_to_apply||!window.confirm(`Spara autoschemat för ${preview.scheduled_count} matcher? Befintliga, spelade och låsta matcher bevaras.`))return;setBusy(true);setError("");setMessage("");try{const result=await api<GenerationPreview>(`/api/admin/cups/${cupId}/schedule/generate`,{method:"POST",body:JSON.stringify({allow_partial:false})},token);setMessage(`${result.applied_count||result.scheduled_count} matcher schemalagda. Förslaget räknades om på servern precis före sparning.`);setPreview(null);setData(await api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token));}catch(err){setError(err instanceof Error?err.message:"Autoschemat kunde inte sparas.");}finally{setBusy(false);}}
  if(!data)return <section className="admin-panel admin-teams" id="schedule"><div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Schema</h2><p>{error||"Hämtar riktiga matcher…"}</p></section>;
  return <section className="admin-panel admin-teams" id="schedule">
    <div className="admin-panel__top"><span>07 / SCHEMA</span><strong>{data.scheduled_count}/{data.match_count} SCHEMALAGDA</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Matchschema</h2><p>Manuell schemaredigering och preview-first autoschema mot CupNavis riktiga schemamotor. Befintliga, spelade och låsta matcher behandlas som fasta begränsningar.</p></div><span className="admin-lock">SAFE GENERATOR</span></div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
    <div className="admin-dashboard-grid" style={{marginBottom:18}}>
      <article className="admin-panel"><strong>{data.match_count}</strong><small>matcher totalt</small></article>
      <article className="admin-panel"><strong>{data.scheduled_count}</strong><small>schemalagda</small></article>
      <article className="admin-panel"><strong>{data.unscheduled_count}</strong><small>utan tid/plan</small></article>
    </div>
    {data.schedule_dirty&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>Kontroll krävs</b> · schemat är markerat som ändrat. Publicera inte innan krockar och vilotider har kontrollerats.</div>}
    <div className="admin-panel" style={{marginBottom:18}}>
      <div className="admin-cupinfo__head"><div><h3>Autoschema</h3><p>Steg 1 räknar bara fram ett förslag. Steg 2 sparar först efter din bekräftelse och räknar om förslaget på servern så att en gammal preview aldrig skrivs in.</p></div><div className="admin-team-actions"><button type="button" onClick={()=>void previewSchedule()} disabled={busy||data.unscheduled_count===0}>{busy?"Arbetar…":"Förhandsgranska autoschema"}</button>{preview?.safe_to_apply&&<button type="button" onClick={()=>void applySchedule()} disabled={busy}>Använd förslag</button>}</div></div>
      {preview&&<div><div className="admin-dashboard-grid" style={{marginTop:12,marginBottom:12}}><article><strong>{preview.scheduled_count}</strong><small>nya tider</small></article><article><strong>{preview.preserved_count}</strong><small>bevarade matcher</small></article><article><strong>{preview.unresolved_count}</strong><small>olösta</small></article></div><small>Motor: {preview.engine}</small>{preview.updates.length>0&&<div className="admin-team-list" style={{marginTop:12}}>{preview.updates.slice(0,12).map(update=>{const match=matchById.get(update.id);return <article key={`preview-${update.id}`}><div><strong>{match?`${match.home_label} – ${match.away_label}`:`Match ${update.id}`}</strong><small>{update.stage||match?.stage||"Match"}</small></div><div><strong>{shortTime(update.scheduled_start)}</strong><small>Plan {update.pitch_number}{update.referee_id?` · domare ${update.referee_id}`:""}</small></div></article>})}{preview.updates.length>12&&<div className="admin-empty"><span>+ {preview.updates.length-12} ytterligare schemaläggningar i förslaget</span></div>}</div>}{preview.unresolved_count>0&&<div className="admin-code-placeholder" style={{marginTop:12}}><b>Inte komplett</b> · {preview.unresolved_count} matcher kan inte placeras säkert ännu. CupNavi sparar inte ett ofullständigt autoschema via standardknappen.</div>}</div>}
    </div>
    <div className="admin-team-actions" style={{marginBottom:16}}><button type="button" onClick={()=>setFilter("all")} disabled={filter==="all"}>Alla</button><button type="button" onClick={()=>setFilter("scheduled")} disabled={filter==="scheduled"}>Schemalagda</button><button type="button" onClick={()=>setFilter("unscheduled")} disabled={filter==="unscheduled"}>Oschemalagda</button></div>
    <div className="admin-team-list">
      {visible.length?visible.map(match=><article key={match.id} style={{alignItems:"end"}}>
        <div style={{flex:1,minWidth:220}}><strong>{match.home_label} – {match.away_label}</strong><small>{match.stage}{match.group_name?` · ${match.group_name}`:""}{match.match_no?` · match ${match.match_no}`:""}{match.played?" · SPELAD":match.schedule_locked?" · LÅST":""}</small></div>
        <label style={{minWidth:190}}>Tid<input type="datetime-local" disabled={busy||match.played||match.schedule_locked} value={localInput(match.scheduled_start)} onChange={e=>patchMatch(match.id,{scheduled_start:e.target.value||null})}/></label>
        <label style={{minWidth:110}}>Plan<select disabled={busy||match.played||match.schedule_locked} value={match.pitch_number??""} onChange={e=>patchMatch(match.id,{pitch_number:e.target.value?Number(e.target.value):null})}><option value="">Ingen</option>{Array.from({length:data.pitch_count},(_,i)=>i+1).map(n=><option key={n} value={n}>Plan {n}</option>)}</select></label>
        <div className="admin-team-actions"><button type="button" disabled={busy||match.played||match.schedule_locked||!match.scheduled_start||!match.pitch_number} onClick={()=>saveMatch(match)}>Spara</button>{match.scheduled_start&&<button type="button" disabled={busy||match.played||match.schedule_locked} onClick={()=>clearMatch(match)}>Gör oschemalagd</button>}</div>
      </article>):<div className="admin-empty"><strong>Inga matcher i filtret</strong><span>Byt filter eller skapa gruppmatcher i det avancerade schemaflödet.</span></div>}
    </div>
    <div className="admin-form-footer"><span>Manuella ändringar flyttar aldrig andra matcher automatiskt. Autoschema kräver alltid en separat förhandsgranskning.</span><button type="button" onClick={()=>void load()} disabled={busy}>{busy?"Hämtar…":"Uppdatera schema"}</button></div>
  </section>;
}