"use client";

import { useCallback, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";
const AUTO_REVIEW_PREFIX = "cupnavi_playoff_review_seen_";
const IMPORT_REVIEW_NEXT_EVENT = "cupnavi:import-review-next";

type PlayoffRow = {
  time?:string|null;
  venue?:string|null;
  label?:string|null;
  home_source?:string|null;
  away_source?:string|null;
  duration?:string|null;
};
type ReviewPayload = {
  available:boolean;
  source_name?:string|null;
  playoff_matches:PlayoffRow[];
  playoff_rule_values?:Record<string,unknown>;
  existing_playoff_matches:number;
  existing_brackets:number;
};
type PitchReviewPayload = { available:boolean };
type CommitPayload = { imported:number; bracket_id:number; validation?:{ready?:boolean;issue_count?:number} };

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

export default function PlayoffImportReview() {
  const [cupId,setCupId] = useState<number|null>(null);
  const [review,setReview] = useState<ReviewPayload|null>(null);
  const [rows,setRows] = useState<PlayoffRow[]>([]);
  const [open,setOpen] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [reviewTick,setReviewTick] = useState(0);

  const load = useCallback(async (nextCupId:number) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setReview(null); return; }
    try {
      const data = await request<ReviewPayload>(`/api/admin/cups/${nextCupId}/import/playoffs`,token);
      setReview(data);
      setRows((data.playoff_matches || []).map(row=>({...row})));
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
    const advance = () => setReviewTick(value=>value+1);
    window.addEventListener(IMPORT_REVIEW_NEXT_EVENT,advance);
    return ()=>window.removeEventListener(IMPORT_REVIEW_NEXT_EVENT,advance);
  },[]);

  useEffect(()=>{
    if (!cupId || !review?.available || !rows.length || open || busy || review.existing_brackets > 0 || review.existing_playoff_matches > 0) return;
    const key = `${AUTO_REVIEW_PREFIX}${cupId}`;
    if (sessionStorage.getItem(key)) return;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    let cancelled = false;
    void request<PitchReviewPayload>(`/api/admin/cups/${cupId}/import/pitch-windows`,token)
      .then(pitchReview=>{
        if (cancelled || pitchReview.available) return;
        sessionStorage.setItem(key,"1");
        setRows(review.playoff_matches.map(row=>({...row})));
        setError("");
        setOpen(true);
      })
      .catch(()=>{
        if (cancelled) return;
        sessionStorage.setItem(key,"1");
        setRows(review.playoff_matches.map(row=>({...row})));
        setError("");
        setOpen(true);
      });
    return ()=>{cancelled=true;};
  },[cupId,review,rows.length,open,busy,reviewTick]);

  function updateRow(index:number,key:keyof PlayoffRow,value:string) {
    setRows(current=>current.map((row,rowIndex)=>rowIndex===index?{...row,[key]:value||null}:row));
  }

  async function commit() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token || !cupId || !review) return;
    if (!window.confirm(`Importera ${rows.length} granskade slutspelsmatcher?\n\nCupNavi skapar slutspelsträdet som opublicerat underlag. Befintligt slutspel skrivs aldrig över.`)) return;
    setBusy(true); setError("");
    try {
      const result = await request<CommitPayload>(`/api/admin/cups/${cupId}/import/playoffs`,token,{
        method:"POST",
        body:JSON.stringify({playoff_matches:rows,playoff_rule_values:review.playoff_rule_values || {}}),
      });
      if (!result.imported) throw new Error("Inga slutspelsmatcher importerades.");
      setOpen(false);
      await load(cupId);
      window.location.hash="playoffs";
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Slutspelet kunde inte importeras.");
    } finally { setBusy(false); }
  }

  if (!review?.available || review.existing_brackets > 0 || review.existing_playoff_matches > 0) return null;

  return <>
    <section className="admin-panel" style={{maxWidth:1120,margin:"12px auto",borderWidth:2}}>
      <div className="admin-panel__top"><span>IMPORT · SLUTSPEL</span><strong>{rows.length} MATCHER HITTADES</strong></div>
      <div style={{display:"flex",justifyContent:"space-between",gap:16,alignItems:"center",flexWrap:"wrap"}}>
        <div>
          <h2 style={{marginBottom:5}}>Slutspel väntar på granskning</h2>
          <p style={{margin:0,maxWidth:680}}>Foto/PDF-underlaget innehåller ett slutspel. CupNavi skriver inte in det förrän du har kontrollerat matchnamn, deltagarkällor, tider och planer.</p>
        </div>
        <button type="button" onClick={()=>{setRows(review.playoff_matches.map(row=>({...row})));setError("");setOpen(true);}}>Granska slutspel →</button>
      </div>
    </section>

    {open && <div className="cup-create-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget&&!busy)setOpen(false);}}>
      <section className="cup-create-dialog" role="dialog" aria-modal="true" aria-labelledby="playoff-import-title" style={{maxWidth:1040,width:"min(1040px,calc(100vw - 20px))"}}>
        <div className="cup-create-dialog__head">
          <div><span>SLUTSPELSIMPORT</span><h2 id="playoff-import-title">Kontrollera trädet innan import</h2></div>
          <button type="button" className="cup-create-close" onClick={()=>!busy&&setOpen(false)} aria-label="Stäng">×</button>
        </div>
        <p className="cup-create-lead">Deltagarkällor kan vara exakta lagnamn, exempelvis <strong>1:a Grupp A</strong> eller <strong>Vinnare semifinal 1</strong>. Om en koppling inte kan bevisas stoppas hela importen utan att ett halvt träd sparas.</p>
        {review.source_name && <p style={{fontSize:13}}><strong>Underlag:</strong> {review.source_name}</p>}

        <div style={{display:"grid",gap:10,maxHeight:"52vh",overflowY:"auto",overflowX:"hidden",paddingRight:4}}>
          {rows.map((row,index)=><div key={index} style={{border:"1px solid currentColor",borderRadius:10,padding:10,minWidth:0}}>
            <strong>Match {index+1}</strong>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:7,marginTop:8,minWidth:0}}>
              <label>Matchnamn<input value={row.label||""} onChange={event=>updateRow(index,"label",event.target.value)} placeholder="Semifinal 1" /></label>
              <label>Tid<input value={row.time||""} onChange={event=>updateRow(index,"time",event.target.value)} placeholder="14:00" /></label>
              <label>Lag/källa 1<input value={row.home_source||""} onChange={event=>updateRow(index,"home_source",event.target.value)} placeholder="1:a Grupp A" /></label>
              <label>Lag/källa 2<input value={row.away_source||""} onChange={event=>updateRow(index,"away_source",event.target.value)} placeholder="2:a Grupp B" /></label>
              <label>Plan<input value={row.venue||""} onChange={event=>updateRow(index,"venue",event.target.value)} /></label>
            </div>
          </div>)}
        </div>

        {review.playoff_rule_values && Object.values(review.playoff_rule_values).some(value=>value!=null&&value!=="") && <details style={{marginTop:12}}><summary><strong>Särskilda slutspelsregler hittades</strong></summary><pre style={{whiteSpace:"pre-wrap",fontSize:12,overflowWrap:"anywhere"}}>{JSON.stringify(review.playoff_rule_values,null,2)}</pre></details>}
        {error && <p className="cup-create-error" role="alert">{error}</p>}
        <div className="cup-create-actions"><button type="button" className="is-secondary" onClick={()=>setOpen(false)} disabled={busy}>Avbryt</button><button type="button" onClick={()=>void commit()} disabled={busy||!rows.length}>{busy?"Validerar och importerar…":"✓ Importera granskat slutspel"}</button></div>
      </section>
    </div>}
  </>;
}
