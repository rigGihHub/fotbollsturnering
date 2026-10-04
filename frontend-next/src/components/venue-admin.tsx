"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { mergeVenueRows } from "../lib/admin-draft";
import { useAdminDraft } from "../lib/use-admin-draft";
import AdminDraftStatus from "./admin-draft-status";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const PITCH_WINDOWS_UPDATED_EVENT = "cupnavi:pitch-windows-updated";

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
  const {data,setData,accept,dirty} = useAdminDraft<VenuePayload>(`${cupId}:venues`);
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState("");
  const [error,setError] = useState("");

  const load = useCallback(async()=>{
    setBusy(true); setError("");
    try { accept(await api<VenuePayload>(`/api/admin/cups/${cupId}/venues`,{},token),true); }
    catch(err) { setError(err instanceof Error?err.message:"Planer och tider kunde inte hämtas."); }
    finally { setBusy(false); }
  },[cupId,token,accept]);

  useEffect(()=>{ void load(); },[load]);

  async function saveRules(event:FormEvent) {
    event.preventDefault(); if (!data) return;
    if(data.rules.pitch_count<data.pitches.length&&!window.confirm("Färre planer gör att planrader och deras osparade tider döljs. Vill du minska antalet planer?"))return;
    const snapshot=data;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved=await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/rules`,{
        method:"PUT",body:JSON.stringify(data.rules)
      },token);
      accept(saved); setData(mergeVenueRows(snapshot,saved)); setMessage(saved.scheduled_count?"Grundinställningarna är sparade. Befintliga matcher är orörda och schemat är markerat för kontroll.":"Grundinställningarna är sparade. Fortsätt med plannamn och öppettider nedan.");
    } catch(err) { setError(err instanceof Error?err.message:"Planinställningarna kunde inte sparas."); }
    finally { setBusy(false); }
  }

  async function saveEverything() {
    if (!data) return;
    if(data.rules.pitch_count!==data.pitches.length){setError("Uppdatera antal planer innan du sparar hela upplägget.");return;}
    const snapshot=data;
    setBusy(true); setError(""); setMessage("");
    try {
      await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/rules`,{method:"PUT",body:JSON.stringify(snapshot.rules)},token);
      for (const pitch of snapshot.pitches) {
        await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/pitches/${pitch.pitch_number}`,{method:"PUT",body:JSON.stringify({name:pitch.name,address:pitch.address || null})},token);
      }
      const days=snapshot.windows.filter((row,index,rows)=>rows.findIndex(w=>w.pitch_number===row.pitch_number&&w.play_date===row.play_date)===index);
      for (const row of days) {
        await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/pitches/${row.pitch_number}/windows/${row.play_date}`,{method:"PUT",body:JSON.stringify({intervals:snapshot.windows.filter(w=>w.pitch_number===row.pitch_number&&w.play_date===row.play_date).map(({start_time,end_time})=>({start_time,end_time})),confirmed:true})},token);
      }
      const verified=await api<VenuePayload>(`/api/admin/cups/${cupId}/venues`,{},token);
      const missing=snapshot.windows.some(expected=>!verified.windows.some(actual=>actual.pitch_number===expected.pitch_number&&actual.play_date===expected.play_date&&actual.start_time===expected.start_time&&actual.end_time===expected.end_time&&Boolean(actual.confirmed)));
      if(missing)throw new Error("Servern kunde inte verifiera alla plantider efter sparningen.");
      accept(verified); setMessage(`Alla ${verified.pitches.length} planer och ${verified.windows.length} plantider är sparade och verifierade.`); window.dispatchEvent(new Event(PITCH_WINDOWS_UPDATED_EVENT));
      if(window.location.hash==="#venues")window.location.hash="rules";
    } catch(err) { setError(err instanceof Error?err.message:"Planer och tider kunde inte sparas komplett."); }
    finally { setBusy(false); }
  }

  function patchPitch(number:number, patch:Partial<Pitch>) {
    if (!data) return;
    setData({...data,pitches:data.pitches.map(p=>p.pitch_number===number?{...p,...patch}:p)});
  }
  function patchWindow(row:PitchWindow, patch:Partial<PitchWindow>) {
    if (!data) return;
    setData({...data,windows:data.windows.map(w=>w===row?{...w,...patch,confirmed:false}:w)});
  }

  if (!data) return <section className="admin-panel admin-teams" id="venues"><div className="admin-panel__top"><span>04 / PLANER & TIDER</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Planer & tider</h2><p>{error || "Hämtar cupens plankapacitet…"}</p></section>;

  return <section className="admin-panel admin-teams" id="venues">
    <div className="admin-panel__top"><span>04 / PLANER & TIDER</span><strong>{data.rules.pitch_count} SPELYTOR · {data.dates.length} CUPDAGAR</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Planer & tider</h2><p>Berätta vilka planer som kan användas och när varje plan är öppen. CupNavi använder detta när schemat skapas.</p></div><span className="admin-lock">STEG 1 AV 3</span></div>
    {(error||message) && <div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Sparat"}</b> · {error||message}</div>}
    {data.scheduled_count>0 && <div className="admin-code-placeholder" style={{marginBottom:16}}><b>{data.scheduled_count} schemalagda matcher</b> · ändringar här flyttar aldrig matcher automatiskt. {data.schedule_dirty?"Schemat behöver redan kontrolleras.":"Vid ändring markeras schemat för kontroll."}</div>}

    <fieldset disabled={busy} className="admin-edit-fields">
    <form onSubmit={saveRules} className="admin-team-editor">
      <div className="admin-form-grid">
        <label>Hur många planer används samtidigt?<input type="number" min={1} max={50} value={data.rules.pitch_count} onChange={e=>setData({...data,rules:{...data.rules,pitch_count:Number(e.target.value)}})} required /></label>
        <label>Har planerna samma öppettider?<select value={data.rules.synchronized_pitch_times?"sync":"dynamic"} onChange={e=>setData({...data,rules:{...data.rules,synchronized_pitch_times:e.target.value==="sync"}})}><option value="dynamic">Nej, ange tid för varje plan</option><option value="sync">Ja, samma tider för alla planer</option></select></label>
        {data.rules.synchronized_pitch_times&&<>
          <label>Första avspark på alla planer<input type="time" value={data.rules.first_match_time} onChange={e=>setData({...data,rules:{...data.rules,first_match_time:e.target.value}})} /></label>
          <label>Sista avspark på alla planer<input type="time" value={data.rules.latest_kickoff_time} onChange={e=>setData({...data,rules:{...data.rules,latest_kickoff_time:e.target.value}})} /></label>
        </>}
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={data.rules.consider_pitch_travel} onChange={e=>setData({...data,rules:{...data.rules,consider_pitch_travel:e.target.checked}})} /> Ta hänsyn till restid mellan planer</label>
      </div>
      {!data.rules.synchronized_pitch_times&&<p className="admin-inline-guidance"><strong>Egna tider per plan är valt.</strong> Du anger start och slut för varje plan i steg 3 nedan. Ingen gemensam sluttid används.</p>}
      <div className="admin-form-footer"><span>Lägger till eller döljer planrader. Plannamn och tider sparas när du fortsätter.</span><button type="submit" disabled={busy}>{busy?"Sparar…":"Uppdatera antal planer"}</button></div>
    </form>

    <div className="admin-section-heading"><span>STEG 2 AV 3</span><h3>Namnge planerna</h3><p>Adressen är valfri och behövs främst om planerna ligger på olika platser.</p></div>
    <div className="admin-team-list admin-venue-list">
      {data.pitches.map(pitch=><article key={pitch.pitch_number} style={{alignItems:"end"}}>
        <div style={{flex:1}}><strong>#{pitch.pitch_number} · {pitch.name}</strong><small>{pitch.address || "Adress saknas"}{pitch.address_verified?" · verifierad adress":""}</small></div>
        <label style={{minWidth:180}}>Plannamn<input value={pitch.name} onChange={e=>patchPitch(pitch.pitch_number,{name:e.target.value})} /></label>
        <label style={{minWidth:220}}>Adress<input value={pitch.address || ""} onChange={e=>patchPitch(pitch.pitch_number,{address:e.target.value})} placeholder="Valfri adress" /></label>

      </article>)}
    </div>

    <div className="admin-section-heading"><span>STEG 3 AV 3</span><h3>Öppettider per plan och cupdag</h3><p>Samma plan kan ha flera pass samma dag. Luckor mellan passen är stängda för matcher. Alla tider sparas tillsammans när du fortsätter.</p><p>{data.rules.synchronized_pitch_times?"Kontrollera att samma tider gäller för alla planer.":"Ange när varje enskild plan kan användas. Dessa tider ersätter en gemensam sluttid."}</p></div>
    <div className="admin-team-list admin-window-list">
      {data.dates.map(playDate=><div key={playDate} style={{display:"grid",gap:8}}>
        <strong>{playDate}</strong>
        {data.windows.filter(w=>w.play_date===playDate).map((row,index)=>{
          const pitch=data.pitches.find(p=>p.pitch_number===row.pitch_number);
          const pitchWindows=data.windows.filter(w=>w.pitch_number===row.pitch_number&&w.play_date===playDate);
          const isLastPitchWindow=pitchWindows[pitchWindows.length-1]===row;
          return <article key={`${playDate}-${index}`}>
            <div style={{minWidth:160}}><strong>{pitch?.name || `Plan ${row.pitch_number}`}</strong><small>{row.confirmed?"Bekräftad tid":"Standardtid – bekräfta vid sparning"}</small></div>
            <label>Start<input type="time" value={row.start_time} onChange={e=>patchWindow(row,{start_time:e.target.value})} /></label>
            <label>Slut<input type="time" value={row.end_time} onChange={e=>patchWindow(row,{end_time:e.target.value})} /></label>
            <div className="admin-window-actions">

              {isLastPitchWindow&&<button type="button" disabled={busy} onClick={()=>setData({...data,windows:[...data.windows,{...row,start_time:row.end_time,end_time:"",confirmed:false}]})}>Lägg till tidsfönster</button>}
              {pitchWindows.length>1&&<button type="button" disabled={busy} onClick={()=>setData({...data,windows:data.windows.filter(w=>w!==row)})}>Ta bort</button>}
            </div>
          </article>;
        })}
      </div>)}
    </div>
    {data.rules.pitch_count!==data.pitches.length?<p className="admin-inline-guidance">Uppdatera antal planer ovan innan du fortsätter.</p>:data.pitches.some(p=>!p.name.trim())?<p className="admin-inline-guidance">Alla planer behöver namn innan du fortsätter.</p>:data.windows.some(w=>!w.start_time||!w.end_time||w.start_time>=w.end_time)?<p className="admin-inline-guidance">Fyll i start- och sluttid för alla pass. Sluttiden ska vara efter starttiden.</p>:null}
    <AdminDraftStatus dirty={dirty} busy={busy} error={error}/>
    <div className="admin-next-step"><div><strong>Spara hela planupplägget</strong><span>Alla plannamn och tider sparas tillsammans innan du går vidare.</span></div><button data-admin-save-next type="button" disabled={busy||data.rules.pitch_count!==data.pitches.length||data.windows.some(row=>!row.start_time||!row.end_time||row.start_time>=row.end_time)||data.pitches.some(pitch=>!pitch.name.trim())} onClick={()=>void saveEverything()}>{busy?"Sparar och kontrollerar…":"Spara och fortsätt till Regler →"}</button></div>
    </fieldset>
  </section>;
}
