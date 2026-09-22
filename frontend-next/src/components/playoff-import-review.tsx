"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./playoff-import-review.module.css";
import { playoffImportRules } from "../lib/playoff-import-rules";
import { CLIENT_API_BASE } from "../lib/client-api";
import { OPEN_PLAYOFF_REVIEW_EVENT, PLAYOFF_REVIEW_REQUEST_KEY } from "../lib/open-playoff-review";

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
  const controller = new AbortController();
  const timeout = window.setTimeout(()=>controller.abort(),45000);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store",signal:controller.signal});
  } catch (err) {
    if (controller.signal.aborted) throw new Error("Servern svarade inte i tid. Dina ändringar finns kvar här. Kontrollera anslutningen och försök igen.");
    throw err;
  } finally { window.clearTimeout(timeout); }
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
  const [requested,setRequested] = useState(false);
  const [loading,setLoading] = useState(true);
  const loadGeneration = useRef(0);
  const saving = useRef(false);
  const readableRules = playoffImportRules(review?.playoff_rule_values);

  const load = useCallback(async (nextCupId:number) => {
    const generation = ++loadGeneration.current;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setReview(null); setLoading(false); setError("Logga in för att granska slutspelet."); return; }
    setLoading(true);
    setError("");
    try {
      const data = await request<ReviewPayload>(`/api/admin/cups/${nextCupId}/import/playoffs`,token);
      if (generation !== loadGeneration.current) return;
      setReview(data);
      setRows((data.playoff_matches || []).map(row=>({...row})));
    } catch (err) {
      if (generation !== loadGeneration.current) return;
      setReview(null);
      setError(err instanceof Error ? err.message : "Slutspelsunderlaget kunde inte hämtas.");
    } finally {
      if (generation === loadGeneration.current) setLoading(false);
    }
  },[]);

  useEffect(()=>{
    let current = activeCupId();
    setCupId(current);
    if (current) void load(current);
    const timer = window.setInterval(()=>{
      const next = activeCupId();
      if (next !== current) {
        ++loadGeneration.current;
        current = next;
        setOpen(false); setReview(null); setRows([]); setError("");
        setCupId(next);
        if (next) void load(next); else setReview(null);
      }
    },1000);
    return ()=>{window.clearInterval(timer);++loadGeneration.current;};
  },[load]);

  useEffect(()=>{
    const sync = () => setRequested(sessionStorage.getItem(PLAYOFF_REVIEW_REQUEST_KEY) === String(activeCupId()));
    sync();
    window.addEventListener(OPEN_PLAYOFF_REVIEW_EVENT,sync);
    return ()=>window.removeEventListener(OPEN_PLAYOFF_REVIEW_EVENT,sync);
  },[cupId]);

  useEffect(()=>{
    if (!requested || loading || !review?.available || !cupId) return;
    sessionStorage.removeItem(PLAYOFF_REVIEW_REQUEST_KEY);
    setRequested(false);
    if (review.existing_brackets || review.existing_playoff_matches) return;
    sessionStorage.setItem(`${AUTO_REVIEW_PREFIX}${cupId}`,"1");
    setRows(review.playoff_matches.map(row=>({...row})));
    setError(""); setOpen(true);
  },[requested,loading,review,cupId]);

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
    if (saving.current) return;
    if (!token || !cupId || !review) { setError("Inloggningen eller cupunderlaget saknas. Öppna cupen igen; inget har sparats."); return; }
    if (activeCupId() !== cupId) { setError("Aktiv cup har ändrats. Öppna granskningen för rätt cup innan du sparar."); return; }
    saving.current = true;
    setBusy(true); setError("");
    try {
      const result = await request<CommitPayload>(`/api/admin/cups/${cupId}/import/playoffs`,token,{
        method:"POST",
        body:JSON.stringify({playoff_matches:rows,playoff_rule_values:review.playoff_rule_values || {}}),
      });
      if (!result.imported) throw new Error("Inga slutspelsmatcher importerades.");
      setOpen(false);
      if (activeCupId() !== cupId) return;
      window.location.hash="playoffs";
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Slutspelet kunde inte importeras.");
    } finally { saving.current = false; setBusy(false); }
  }

  if (loading) return <section className="admin-panel" role="status">Hämtar slutspelsunderlaget…</section>;
  if (!review && error) return <section className="admin-panel"><p role="alert">{error}</p><button type="button" onClick={()=>cupId&&void load(cupId)}>Försök igen</button></section>;
  if (requested && !review?.available) return <section className="admin-panel" role="status">Inget importerat slutspel finns att granska för den här cupen.</section>;
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

    {open && <div className={styles.backdrop} role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget&&!busy)setOpen(false);}}>
      <section className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="playoff-import-title" aria-busy={busy}>
        <div className={styles.header}>
          <div><span>SLUTSPELSIMPORT</span><h2 id="playoff-import-title">Granska slutspelet</h2></div>
          <button type="button" className={styles.close} disabled={busy} onClick={()=>setOpen(false)} aria-label="Stäng">×</button>
        </div>
        <div className={styles.body}>
          <p>Kontrollera matcher, tider och planer. Lagen kan anges som gruppplaceringar, till exempel <strong>1:a Grupp A</strong>, eller <strong>Vinnare semifinal 1</strong>.</p>
          {review.source_name && <p><strong>Underlag:</strong> {review.source_name}</p>}
          <div className={styles.matches}>
            {rows.map((row,index)=><div key={index} className={styles.match}>
              <strong>Match {index+1}</strong>
              <div className={styles.fields}>
                <label>Match eller grupp<input value={row.label||""} disabled={busy} onChange={event=>updateRow(index,"label",event.target.value)} placeholder="Semifinal 1 eller Guldgruppen" /></label>
                <label>Tid<input value={row.time||""} disabled={busy} onChange={event=>updateRow(index,"time",event.target.value)} placeholder="14:00" /></label>
                <label>Hemmalag eller placering<input value={row.home_source||""} disabled={busy} onChange={event=>updateRow(index,"home_source",event.target.value)} placeholder="1:a Grupp A" /></label>
                <label>Bortalag eller placering<input value={row.away_source||""} disabled={busy} onChange={event=>updateRow(index,"away_source",event.target.value)} placeholder="2:a Grupp B" /></label>
                <label>Plan<input value={row.venue||""} disabled={busy} onChange={event=>updateRow(index,"venue",event.target.value)} /></label>
              </div>
            </div>)}
          </div>
          {readableRules.length > 0 && <section className={styles.rules} aria-label="Regler i underlaget"><h3>Regler i underlaget</h3><dl>{readableRules.map(rule=><div key={rule.label}><dt>{rule.label}</dt><dd>{rule.value}</dd></div>)}</dl></section>}
        </div>
        <div className={styles.footer}>
          {error && <div className={styles.error} role="alert">{error}</div>}
          <p>Sparas som utkast. Befintligt slutspel skrivs aldrig över.</p>
          <div className={styles.actions}><button type="button" onClick={()=>setOpen(false)} disabled={busy}>Avbryt</button><button type="button" onClick={()=>void commit()} disabled={busy||!rows.length}>{busy?"Sparar…":"Importera granskat slutspel"}</button></div>
        </div>
      </section>
    </div>}
  </>;
}
