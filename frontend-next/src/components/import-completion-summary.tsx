"use client";

import { useCallback, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Counts = {
  teams:number; groups:number; matches:number; pitches:number;
  pitch_windows:number; playoff_matches:number; rules?:number;
};
type Summary = {
  available:boolean;
  complete?:boolean;
  source_name?:string|null;
  expected?:Counts;
  actual?:Counts;
  pending?:string[];
  warnings?:string[];
};

function activeCupId() {
  const fromUrl = Number(new URLSearchParams(window.location.search).get("cup"));
  if (Number.isFinite(fromUrl) && fromUrl > 0) return fromUrl;
  const stored = Number(localStorage.getItem(CUP_KEY));
  return Number.isFinite(stored) && stored > 0 ? stored : null;
}

async function loadSummary(cupId:number):Promise<Summary|null> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const response = await fetch(`${API_BASE}/api/admin/cups/${cupId}/import/summary`,{
    headers:{Authorization:`Bearer ${token}`},cache:"no-store",
  });
  if (!response.ok) return null;
  return response.json();
}

function Stat({label,found,saved}:{label:string;found:number;saved:number}) {
  return <div style={{border:"1px solid currentColor",borderRadius:10,padding:"9px 11px",minWidth:0}}>
    <strong style={{fontSize:18}}>{saved}</strong>
    <span style={{display:"block",fontSize:12}}>{label} i cupen</span>
    {found!==saved && <small style={{opacity:.75}}>{found} hittades i underlaget</small>}
  </div>;
}

export default function ImportCompletionSummary() {
  const [summary,setSummary] = useState<Summary|null>(null);
  const [cupId,setCupId] = useState<number|null>(null);

  const refresh = useCallback(async (id:number)=>{
    const next = await loadSummary(id);
    setSummary(next);
  },[]);

  useEffect(()=>{
    let current = activeCupId();
    setCupId(current);
    if (current) void refresh(current);
    const timer = window.setInterval(()=>{
      const next = activeCupId();
      if (next !== current) {
        current = next; setCupId(next); setSummary(null);
      }
      if (current) void refresh(current);
    },2500);
    return ()=>window.clearInterval(timer);
  },[refresh]);

  if (!cupId || !summary?.available || !summary.complete || !summary.expected || !summary.actual) return null;
  const expected=summary.expected, actual=summary.actual;

  return <section className="admin-panel" style={{maxWidth:1120,margin:"12px auto",borderWidth:2}} aria-label="Import klar">
    <div className="admin-panel__top"><span>IMPORT · KLAR</span><strong>✓ GRANSKNINGSKEDJAN ÄR FÄRDIG</strong></div>
    <div>
      <h2 style={{marginBottom:5}}>Import klar</h2>
      <p style={{marginTop:0,maxWidth:760}}>CupNavi har gått igenom de delar av foto/PDF-underlaget som kräver särskild granskning. Siffrorna nedan skiljer på vad som hittades och vad som faktiskt finns sparat i cupen.</p>
      {summary.source_name && <p style={{fontSize:13}}><strong>Underlag:</strong> {summary.source_name}</p>}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(125px,1fr))",gap:8,marginTop:12}}>
        <Stat label="lag" found={expected.teams} saved={actual.teams}/>
        <Stat label="grupper" found={expected.groups} saved={actual.groups}/>
        <Stat label="matcher" found={expected.matches} saved={actual.matches}/>
        <Stat label="planer" found={expected.pitches} saved={actual.pitches}/>
        <Stat label="plantider" found={expected.pitch_windows} saved={actual.pitch_windows}/>
        <Stat label="slutspelsmatcher" found={expected.playoff_matches} saved={actual.playoff_matches}/>
      </div>
      {!!summary.warnings?.length && <details style={{marginTop:12}}><summary><strong>Varningar från avläsningen ({summary.warnings.length})</strong></summary><ul>{summary.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></details>}
      <p style={{fontSize:13,marginBottom:0,marginTop:12}}>Importen publicerar aldrig cupen automatiskt. Kontrollera cupöversikten och publicera först när allt ser rätt ut.</p>
    </div>
  </section>;
}
