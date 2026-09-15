"use client";

import { useCallback, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";
const AUTO_REVIEW_PREFIX = "cupnavi_pitch_window_review_seen_";
const IMPORT_REVIEW_NEXT_EVENT = "cupnavi:import-review-next";

type PitchWindowRow = {
  venue?:string|null;
  date?:string|null;
  start_time?:string|null;
  end_time?:string|null;
};

type ReviewPayload = {
  available:boolean;
  source_name?:string|null;
  pitch_windows:PitchWindowRow[];
  found_count:number;
  already_applied_count:number;
};

type CommitPayload = { imported:number; review?:ReviewPayload };

async function request<T>(path:string, token:string, options:RequestInit = {}):Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization",`Bearer ${token}`);
  if (options.body) headers.set("Content-Type","application/json");
  const response = await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const body = await response.json().catch(()=>null);
  if (!response.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : `API-fel ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function activeCupId() {
  const fromUrl = Number(new URLSearchParams(window.location.search).get("cup"));
  if (Number.isFinite(fromUrl) && fromUrl > 0) return fromUrl;
  const stored = Number(localStorage.getItem(CUP_KEY));
  return Number.isFinite(stored) && stored > 0 ? stored : null;
}

export default function PitchWindowImportReview() {
  const [cupId,setCupId] = useState<number|null>(null);
  const [review,setReview] = useState<ReviewPayload|null>(null);
  const [rows,setRows] = useState<PitchWindowRow[]>([]);
  const [open,setOpen] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");

  const load = useCallback(async (nextCupId:number) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setReview(null); return; }
    try {
      const data = await request<ReviewPayload>(`/api/admin/cups/${nextCupId}/import/pitch-windows`,token);
      setReview(data);
      setRows((data.pitch_windows || []).map(row=>({...row})));
    } catch {
      setReview(null);
    }
  },[]);

  useEffect(()=>{
    let current = activeCupId();
    setCupId(current);
    if (current) void load(current);
    const timer = window.setInterval(()=>{
      const next = activeCupId();
      if (next !== current) {
        current = next;
        setCupId(next);
        if (next) void load(next); else setReview(null);
      }
    },1000);
    return ()=>window.clearInterval(timer);
  },[load]);

  useEffect(()=>{
    if (!cupId || !review?.available || !rows.length || open || busy) return;
    const key = `${AUTO_REVIEW_PREFIX}${cupId}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key,"1");
    setRows(review.pitch_windows.map(row=>({...row})));
    setError("");
    setOpen(true);
  },[cupId,review,rows.length,open,busy]);

  function updateRow(index:number,key:keyof PitchWindowRow,value:string) {
    setRows(current=>current.map((row,rowIndex)=>rowIndex===index?{...row,[key]:value||null}:row));
  }

  async function commit() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token || !cupId || !review) return;
    if (!window.confirm(`Spara ${rows.length} granskade plantider?\n\nTiderna blir bekräftade planbegränsningar. Om cupen redan har ett schema markeras det för ny kontroll.`)) return;
    setBusy(true); setError("");
    try {
      const result = await request<CommitPayload>(`/api/admin/cups/${cupId}/import/pitch-windows`,token,{
        method:"POST",
        body:JSON.stringify({pitch_windows:rows}),
      });
      if (!result.imported) throw new Error("Inga plantider importerades.");
      setOpen(false);
      await load(cupId);
      window.dispatchEvent(new Event(IMPORT_REVIEW_NEXT_EVENT));
      window.location.hash="schedule";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plantiderna kunde inte importeras.");
    } finally { setBusy(false); }
  }

  if (!review?.available || !rows.length) return null;

  return <>
    <section className="admin-panel pitch-review-callout" style={{maxWidth:1120,margin:"12px auto",borderWidth:2}}>
      <div className="admin-panel__top"><span>GÖR DETTA FÖRST</span><strong>{rows.length} PLANTIDER ATT BEKRÄFTA</strong></div>
      <div style={{display:"flex",justifyContent:"space-between",gap:16,alignItems:"center",flexWrap:"wrap"}}>
        <div>
          <h2 style={{marginBottom:5}}>Bekräfta när planerna är öppna</h2>
          <p style={{margin:0,maxWidth:680}}>Kontrollera de importerade plantiderna innan du godkänner schemat. Annars går det inte att säkert avgöra om matcherna ryms på respektive plan.</p>
          {review.already_applied_count>0 && <small>{review.already_applied_count} tidsfönster är redan bekräftade och visas därför inte igen.</small>}
        </div>
        <button type="button" className="pitch-review-callout__action" onClick={()=>{setRows(review.pitch_windows.map(row=>({...row})));setError("");setOpen(true);}}>Kontrollera {rows.length} plantider →</button>
      </div>
    </section>

    {open && <div className="cup-create-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget&&!busy)setOpen(false);}}>
      <section className="cup-create-dialog" role="dialog" aria-modal="true" aria-labelledby="pitch-window-import-title" style={{maxWidth:980,width:"min(980px,calc(100vw - 20px))"}}>
        <div className="cup-create-dialog__head">
          <div><span>PLANIMPORT</span><h2 id="pitch-window-import-title">Kontrollera planernas tillgänglighet</h2></div>
          <button type="button" className="cup-create-close" onClick={()=>!busy&&setOpen(false)} aria-label="Stäng">×</button>
        </div>
        <p className="cup-create-lead">Varje rad måste matcha ett befintligt plannamn och ett datum inom cupen. Om något inte stämmer stoppas hela importen i stället för att CupNavi chansar.</p>
        {review.source_name && <p style={{fontSize:13}}><strong>Underlag:</strong> {review.source_name}</p>}

        <div style={{display:"grid",gap:10,maxHeight:"52vh",overflow:"auto",paddingRight:4}}>
          {rows.map((row,index)=><div key={index} style={{border:"1px solid currentColor",borderRadius:10,padding:10}}>
            <strong>Tidsfönster {index+1}</strong>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(180px,100%),1fr))",gap:7,marginTop:8}}>
              <label>Plan / anläggning<input value={row.venue||""} onChange={event=>updateRow(index,"venue",event.target.value)} placeholder="Plan 1" style={{width:"100%"}} /></label>
              <label>Datum<input type="date" value={row.date||""} onChange={event=>updateRow(index,"date",event.target.value)} style={{width:"100%"}} /></label>
              <label>Från<input type="time" value={row.start_time||""} onChange={event=>updateRow(index,"start_time",event.target.value)} style={{width:"100%"}} /></label>
              <label>Till<input type="time" value={row.end_time||""} onChange={event=>updateRow(index,"end_time",event.target.value)} style={{width:"100%"}} /></label>
            </div>
          </div>)}
        </div>

        {error && <p className="cup-create-error" role="alert">{error}</p>}
        <div className="cup-create-actions" style={{flexWrap:"wrap"}}><button type="button" className="is-secondary" onClick={()=>setOpen(false)} disabled={busy}>Avbryt</button><button type="button" onClick={()=>void commit()} disabled={busy||!rows.length}>{busy?"Validerar och sparar…":"✓ Spara granskade plantider"}</button></div>
      </section>
    </div>}
  </>;
}
