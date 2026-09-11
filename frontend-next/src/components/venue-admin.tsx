"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000").replace(/\/$/, "");

type VenueRules = {
  pitch_count:number;
  first_match_time:string;
  latest_kickoff_time:string;
  synchronized_pitch_times:boolean;
  consider_pitch_travel:boolean;
};
type Pitch = { tournament_id:number; pitch_number:number; name:string; address?:string|null; address_verified?:number|boolean };
type PitchWindow = { tournament_id:number; pitch_number:number; play_date:string; start_time:string; end_time:string; confirmed:number|boolean };
type VenuePayload = {
  rules:VenueRules;
  dates:string[];
  pitches:Pitch[];
  windows:PitchWindow[];
  scheduled_count:number;
  max_used_pitch:number;
  schedule_dirty:boolean;
};

async function api<T>(path:string, options:RequestInit, token:string):Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const payload = await response.json().catch(()=>null);
  if (!response.ok) throw new Error(payload?.detail || `API-fel ${response.status}`);
  return payload as T;
}

export default function VenueAdmin({token,cupId}:{token:string;cupId:number}) {
  const [data,setData] = useState<VenuePayload|null>(null);
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState("");
  const [error,setError] = useState("");

  const load = useCallback(async()=>{
    setBusy(true); setError("");
    try { setData(await api<VenuePayload>(`/api/admin/cups/${cupId}/venues`,{},token)); }
    catch(err) { setError(err instanceof Error?err.message:"Planer och tider kunde inte hämtas."); }
    finally { setBusy(false); }
  },[cupId,token]);

  useEffect(()=>{ void load(); },[load]);

  async function saveRules(event:FormEvent) {
    event.preventDefault(); if (!data) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved=await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/rules`,{
        method:"PUT",body:JSON.stringify(data.rules)
      },token);
      setData(saved); setMessage(saved.scheduled_count?"Planinställningarna är sparade. Befintliga matcher är orörda och schemat är markerat för kontroll.":"Planinställningarna är sparade.");
    } catch(err) { setError(err instanceof Error?err.message:"Planinställningarna kunde inte sparas."); }
    finally { setBusy(false); }
  }

  async function savePitch(pitch:Pitch) {
    setBusy(true); setError(""); setMessage("");
    try {
      const saved=await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/pitches/${pitch.pitch_number}`,{
        method:"PUT",body:JSON.stringify({name:pitch.name,address:pitch.address || null})
      },token);
      setData(saved); setMessage(`${pitch.name} har sparats.`);
    } catch(err) { setError(err instanceof Error?err.message:"Planen kunde inte sparas."); }
    finally { setBusy(false); }
  }

  async function saveWindow(windowRow:PitchWindow) {
    setBusy(true); setError(""); setMessage("");
    try {
      const saved=await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/pitches/${windowRow.pitch_number}/windows/${windowRow.play_date}`,{
        method:"PUT",body:JSON.stringify({start_time:windowRow.start_time,end_time:windowRow.end_time,confirmed:true})
      },token);
      setData(saved); setMessage(`Plantiden ${windowRow.play_date} har sparats.`);
    } catch(err) { setError(err instanceof Error?err.message:"Plantiden kunde inte sparas."); }
    finally { setBusy(false); }
  }

  function patchPitch(number:number, patch:Partial<Pitch>) {
    if (!data) return;
    setData({...data,pitches:data.pitches.map(p=>p.pitch_number===number?{...p,...patch}:p)});
  }
  function patchWindow(number:number, playDate:string, patch:Partial<PitchWindow>) {
    if (!data) return;
    setData({...data,windows:data.windows.map(w=>w.pitch_number===number&&w.play_date===playDate?{...w,...patch}:w)});
  }

  if (!data) return <section className="admin-panel admin-teams" id="venues"><div className="admin-panel__top"><span>05 / PLANER & TIDER</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Planer & tider</h2><p>{error || "Hämtar cupens plankapacitet…"}</p></section>;

  return <section className="admin-panel admin-teams" id="venues">
    <div className="admin-panel__top"><span>05 / PLANER & TIDER</span><strong>{data.rules.pitch_count} SPELYTOR · {data.dates.length} CUPDAGAR</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Planer & tillgänglighet</h2><p>Det här är CupNavis riktiga schemagrund. Publika platsmarkörer hanteras separat och blandas inte ihop med spelytorna.</p></div><span className="admin-lock">SCHEMAGRUND AKTIV</span></div>
    {(error||message) && <div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Sparat"}</b> · {error||message}</div>}
    {data.scheduled_count>0 && <div className="admin-code-placeholder" style={{marginBottom:16}}><b>{data.scheduled_count} schemalagda matcher</b> · ändringar här flyttar aldrig matcher automatiskt. {data.schedule_dirty?"Schemat behöver redan kontrolleras.":"Vid ändring markeras schemat för kontroll."}</div>}

    <form onSubmit={saveRules} className="admin-team-editor">
      <div className="admin-form-grid">
        <label>Antal samtidiga planer/spelytor<input type="number" min={1} max={50} value={data.rules.pitch_count} onChange={e=>setData({...data,rules:{...data.rules,pitch_count:Number(e.target.value)}})} required /></label>
        <label>Tidsläge<select value={data.rules.synchronized_pitch_times?"sync":"dynamic"} onChange={e=>setData({...data,rules:{...data.rules,synchronized_pitch_times:e.target.value==="sync"}})}><option value="dynamic">Dynamiska plantider</option><option value="sync">Samma avsparkstider på alla planer</option></select></label>
        <label>Första möjliga avspark<input type="time" value={data.rules.first_match_time} onChange={e=>setData({...data,rules:{...data.rules,first_match_time:e.target.value}})} /></label>
        <label>Sista möjliga avspark<input type="time" value={data.rules.latest_kickoff_time} onChange={e=>setData({...data,rules:{...data.rules,latest_kickoff_time:e.target.value}})} /></label>
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={data.rules.consider_pitch_travel} onChange={e=>setData({...data,rules:{...data.rules,consider_pitch_travel:e.target.checked}})} /> Ta hänsyn till restid mellan planer</label>
      </div>
      <div className="admin-form-footer"><span>Matchlängd och lagvila ligger under Regler; här anger du faktisk plankapacitet.</span><button type="submit" disabled={busy}>{busy?"Sparar…":"Spara plankapacitet"}</button></div>
    </form>

    <div className="admin-team-list" style={{marginTop:18}}>
      {data.pitches.map(pitch=><article key={pitch.pitch_number} style={{alignItems:"end"}}>
        <div style={{flex:1}}><strong>#{pitch.pitch_number} · {pitch.name}</strong><small>{pitch.address || "Adress saknas"}{pitch.address_verified?" · verifierad adress":""}</small></div>
        <label style={{minWidth:180}}>Plannamn<input value={pitch.name} onChange={e=>patchPitch(pitch.pitch_number,{name:e.target.value})} /></label>
        <label style={{minWidth:220}}>Adress<input value={pitch.address || ""} onChange={e=>patchPitch(pitch.pitch_number,{address:e.target.value})} placeholder="Valfri adress" /></label>
        <button type="button" disabled={busy||!pitch.name.trim()} onClick={()=>savePitch(pitch)}>Spara plan</button>
      </article>)}
    </div>

    <div style={{marginTop:24}}><h3>Öppettider per plan och cupdag</h3><p>Varje plan kan ha egna tider. Sluttiden måste vara senare än starttiden.</p></div>
    <div className="admin-team-list">
      {data.dates.map(playDate=><div key={playDate} style={{display:"grid",gap:8}}>
        <strong>{playDate}</strong>
        {data.windows.filter(w=>w.play_date===playDate).map(row=>{
          const pitch=data.pitches.find(p=>p.pitch_number===row.pitch_number);
          return <article key={`${row.pitch_number}-${playDate}`}>
            <div style={{minWidth:160}}><strong>{pitch?.name || `Plan ${row.pitch_number}`}</strong><small>{row.confirmed?"Bekräftad tid":"Standardtid – bekräfta vid sparning"}</small></div>
            <label>Start<input type="time" value={row.start_time} onChange={e=>patchWindow(row.pitch_number,row.play_date,{start_time:e.target.value})} /></label>
            <label>Slut<input type="time" value={row.end_time} onChange={e=>patchWindow(row.pitch_number,row.play_date,{end_time:e.target.value})} /></label>
            <button type="button" disabled={busy||row.start_time>=row.end_time} onClick={()=>saveWindow(row)}>Spara tid</button>
          </article>;
        })}
      </div>)}
    </div>
  </section>;
}
