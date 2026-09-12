"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE=CLIENT_API_BASE;

type RulesPayload={
  sport:string; points_win:number; points_draw:number; points_loss:number; table_tiebreak:string;
  halves:number; minutes_per_half:number; halftime_minutes:number; pitch_break_minutes:number;
  minimum_team_rest_minutes:number; avoid_consecutive_matches:boolean; consecutive_match_break_minutes:number;
  match_duration_minutes:number; scheduled_count:number; completed_count:number; schedule_dirty:boolean;
};

async function api<T>(path:string,options:RequestInit,token:string):Promise<T>{
  const headers=new Headers(options.headers||{}); if(options.body)headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response=await fetch(`${API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
  return payload as T;
}

export default function RulesAdmin({token,cupId}:{token:string;cupId:number}){
  const[data,setData]=useState<RulesPayload|null>(null); const[busy,setBusy]=useState(false);
  const[message,setMessage]=useState(""); const[error,setError]=useState("");
  const load=useCallback(async()=>{setBusy(true);setError("");try{setData(await api<RulesPayload>(`/api/admin/cups/${cupId}/rules`,{},token));}catch(err){setError(err instanceof Error?err.message:"Reglerna kunde inte hämtas.");}finally{setBusy(false);}},[cupId,token]);
  useEffect(()=>{void load();},[load]);
  async function save(event:FormEvent){event.preventDefault();if(!data)return;setBusy(true);setError("");setMessage("");try{const saved=await api<RulesPayload>(`/api/admin/cups/${cupId}/rules`,{method:"PUT",body:JSON.stringify(data)},token);setData(saved);setMessage(saved.scheduled_count?"Reglerna är sparade. Schemat har markerats för kontroll där tidsregler påverkas.":"Reglerna är sparade.");}catch(err){setError(err instanceof Error?err.message:"Reglerna kunde inte sparas.");}finally{setBusy(false);}}
  if(!data)return <section className="admin-panel admin-teams" id="rules"><div className="admin-panel__top"><span>06 / REGLER</span><strong>{busy?"HÄMTAR":"SAKNAS"}</strong></div><h2>Regler</h2><p>{error||"Hämtar cupens regler…"}</p></section>;
  return <section className="admin-panel admin-teams" id="rules">
    <div className="admin-panel__top"><span>06 / REGLER</span><strong>{data.sport.toUpperCase()} · {data.match_duration_minutes} MIN/MATCH</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Tävlings- och schemaregler</h2><p>Poäng, tabellskiljning, matchstruktur, pauser och lagvila. Planer och öppettider ligger separat under Planer & tider.</p></div><span className="admin-lock">RIKTIGA REGLER</span></div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{error?"Fel":"Sparat"}</b> · {error||message}</div>}
    {data.completed_count>0&&<div className="admin-code-placeholder" style={{marginBottom:16}}><b>{data.completed_count} färdigspelade matcher</b> · matchstrukturen är därför låst mot ändringar som skulle göra historiken inkonsekvent.</div>}
    <form onSubmit={save} className="admin-team-editor">
      <h3>Poäng och tabell</h3>
      <div className="admin-form-grid">
        <label>Poäng för vinst<input type="number" min={0} max={10} value={data.points_win} onChange={e=>setData({...data,points_win:Number(e.target.value)})}/></label>
        <label>Poäng för oavgjort<input type="number" min={0} max={10} value={data.points_draw} onChange={e=>setData({...data,points_draw:Number(e.target.value)})}/></label>
        <label>Poäng för förlust<input type="number" min={0} max={10} value={data.points_loss} onChange={e=>setData({...data,points_loss:Number(e.target.value)})}/></label>
        <label>Tabellskiljning<select value={data.table_tiebreak} onChange={e=>setData({...data,table_tiebreak:e.target.value})}><option>Målskillnad först</option><option>Inbördes möten först</option></select></label>
      </div>
      <h3 style={{marginTop:22}}>Matchstruktur</h3>
      <div className="admin-form-grid">
        <label>Halvlekar / perioder<input type="number" min={1} max={4} disabled={data.completed_count>0} value={data.halves} onChange={e=>setData({...data,halves:Number(e.target.value)})}/></label>
        <label>Minuter per halvlek / period<input type="number" min={1} max={90} disabled={data.completed_count>0} value={data.minutes_per_half} onChange={e=>setData({...data,minutes_per_half:Number(e.target.value)})}/></label>
        <label>Paus mellan halvlekar / perioder<input type="number" min={0} max={30} disabled={data.completed_count>0} value={data.halftime_minutes} onChange={e=>setData({...data,halftime_minutes:Number(e.target.value)})}/></label>
        <label>Planpaus mellan matcher<input type="number" min={0} max={60} value={data.pitch_break_minutes} onChange={e=>setData({...data,pitch_break_minutes:Number(e.target.value)})}/></label>
        <label>Minsta lagvila<input type="number" min={0} max={240} value={data.minimum_team_rest_minutes} onChange={e=>setData({...data,minimum_team_rest_minutes:Number(e.target.value)})}/></label>
        <label>Extra paus vid raka matcher<input type="number" min={0} max={180} disabled={!data.avoid_consecutive_matches} value={data.consecutive_match_break_minutes} onChange={e=>setData({...data,consecutive_match_break_minutes:Number(e.target.value)})}/></label>
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={data.avoid_consecutive_matches} onChange={e=>setData({...data,avoid_consecutive_matches:e.target.checked})}/> Undvik raka matcher för samma lag</label>
      </div>
      <div className="admin-form-footer"><span>Beräknad matchtid: <b>{data.match_duration_minutes} minuter</b>. {data.scheduled_count?`${data.scheduled_count} matcher är redan schemalagda.`:"Inga matcher är schemalagda ännu."}</span><button type="submit" disabled={busy}>{busy?"Sparar…":"Spara regler"}</button></div>
    </form>
  </section>;
}
