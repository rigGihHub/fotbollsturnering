"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type SessionPayload = {
  account?: { role?: string | null; is_owner?: boolean };
};

type CreatedCup = {
  id: number;
  name: string;
  public_slug?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_published?: number | boolean;
  role?: string;
};

type CreatedGroup = { id:number; name:string };
type CreatedTeam = { id:number; name:string };
type ImportedTeam = { name:string; group_name?:string|null };
type ImportedMatch = {
  time?:string|null; venue?:string|null; group_name?:string|null;
  home_team?:string|null; away_team?:string|null; stage?:string|null; duration?:string|null;
};
type ImportProposal = {
  tournament_name?:string|null;
  location?:string|null;
  start_date?:string|null;
  end_date?:string|null;
  venues?:string[];
  teams?:ImportedTeam[];
  matches?:ImportedMatch[];
  playoff_matches?:unknown[];
  rules?:string[];
  rule_values?:Record<string,number|null>;
  warnings?:string[];
  source_name?:string|null;
};

type InitialImportResult = {
  saved:boolean;
  snapshot_id?:number|null;
  imported_matches:number;
};

async function request<T>(path: string, options: RequestInit, token: string): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : `API-fel ${response.status}`;
    throw new Error(detail);
  }
  return payload as T;
}

function uniqueGroups(teams:ImportedTeam[]) {
  const found = new Map<string,string>();
  for (const team of teams) {
    const name = (team.group_name || "").trim();
    if (name && !found.has(name.toLocaleLowerCase("sv"))) found.set(name.toLocaleLowerCase("sv"),name);
  }
  return [...found.values()];
}

export default function CupCreateLauncher() {
  const [token, setToken] = useState<string | null>(null);
  const [isOwner, setIsOwner] = useState(false);
  const [open, setOpen] = useState(false);
  const [mode,setMode] = useState<"manual"|"import">("manual");
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [files,setFiles] = useState<File[]>([]);
  const [proposal,setProposal] = useState<ImportProposal|null>(null);
  const [importSchedule,setImportSchedule] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const proposalTeams = proposal?.teams || [];
  const proposalMatches = proposal?.matches || [];
  const proposalGroups = useMemo(()=>uniqueGroups(proposalTeams),[proposalTeams]);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    request<SessionPayload>("/api/admin/session", {}, stored)
      .then(data => {
        const owner = data.account?.role === "owner" || data.account?.is_owner === true;
        if (owner) {
          setToken(stored);
          setIsOwner(true);
        }
      })
      .catch(() => undefined);
  }, []);

  function resetDialog() {
    setMode("manual");
    setName(""); setStartDate(""); setEndDate("");
    setFiles([]); setProposal(null); setImportSchedule(false); setError("");
  }

  function closeDialog() {
    if (busy) return;
    setOpen(false);
    resetDialog();
  }

  function openDialog() {
    resetDialog();
    setOpen(true);
  }

  function goToCup(cup:CreatedCup) {
    localStorage.setItem(CUP_KEY, String(cup.id));
    const url = new URL(window.location.href);
    url.searchParams.set("cup", String(cup.id));
    url.hash = "overview";
    window.location.assign(`${url.pathname}${url.search}${url.hash}`);
  }

  function updateImportedMatch(index:number, key:keyof ImportedMatch, value:string) {
    setProposal(current => {
      if (!current) return current;
      const matches = [...(current.matches || [])];
      matches[index] = {...matches[index],[key]:value || null};
      return {...current,matches};
    });
  }

  async function createCup(event: FormEvent) {
    event.preventDefault();
    if (!token || !name.trim()) return;
    if (startDate && endDate && endDate < startDate) {
      setError("Slutdatum kan inte vara före startdatum.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const cup = await request<CreatedCup>("/api/admin/cups", {
        method: "POST",
        body: JSON.stringify({ name:name.trim(), start_date:startDate || null, end_date:endDate || null }),
      }, token);
      goToCup(cup);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cupen kunde inte skapas.");
      setBusy(false);
    }
  }

  async function analyzeFiles() {
    if (!token || !files.length) return;
    setBusy(true); setError(""); setProposal(null);
    try {
      const form = new FormData();
      files.forEach(file=>form.append("files",file,file.name));
      const result = await request<ImportProposal>("/api/admin/cup-import/analyze",{method:"POST",body:form},token);
      setProposal(result);
      setName(result.tournament_name || "");
      setStartDate(result.start_date || "");
      setEndDate(result.end_date || result.start_date || "");
      setImportSchedule(Boolean(result.matches?.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Underlaget kunde inte läsas.");
    } finally { setBusy(false); }
  }

  async function createFromImport(event:FormEvent) {
    event.preventDefault();
    if (!token || !proposal || !name.trim()) return;
    if (startDate && endDate && endDate < startDate) {
      setError("Slutdatum kan inte vara före startdatum.");
      return;
    }
    if (importSchedule && proposalMatches.length && !startDate) {
      setError("Ange cupens startdatum innan du importerar matchschemat. CupNavi gissar inte vilket datum ett klockslag hör till.");
      return;
    }
    setBusy(true); setError("");
    let cup:CreatedCup|null = null;
    try {
      cup = await request<CreatedCup>("/api/admin/cups",{
        method:"POST",
        body:JSON.stringify({name:name.trim(),start_date:startDate||null,end_date:endDate||null}),
      },token);

      const groupIds = new Map<string,number>();
      for (const groupName of proposalGroups) {
        const group = await request<CreatedGroup>(`/api/admin/cups/${cup.id}/groups`,{
          method:"POST", body:JSON.stringify({name:groupName})
        },token);
        groupIds.set(groupName.toLocaleLowerCase("sv"),group.id);
      }

      for (const row of proposalTeams) {
        const team = await request<CreatedTeam>(`/api/admin/cups/${cup.id}/teams`,{
          method:"POST", body:JSON.stringify({name:row.name})
        },token);
        const groupId = row.group_name ? groupIds.get(row.group_name.trim().toLocaleLowerCase("sv")) : undefined;
        if (groupId) {
          await request(`/api/admin/cups/${cup.id}/teams/${team.id}/group`,{
            method:"PUT", body:JSON.stringify({group_id:groupId})
          },token);
        }
      }

      const venues = (proposal.venues || []).filter(Boolean);
      if (venues.length) {
        await request(`/api/admin/cups/${cup.id}/venues/rules`,{
          method:"PUT", body:JSON.stringify({pitch_count:venues.length})
        },token);
        for (let index=0; index<venues.length; index++) {
          await request(`/api/admin/cups/${cup.id}/venues/pitches/${index+1}`,{
            method:"PUT", body:JSON.stringify({name:venues[index]})
          },token);
        }
      }

      const ruleValues = Object.fromEntries(Object.entries(proposal.rule_values || {}).filter(([,value])=>value != null));
      if (Object.keys(ruleValues).length) {
        await request(`/api/admin/cups/${cup.id}/rules`,{method:"PUT",body:JSON.stringify(ruleValues)},token);
      }

      await request<InitialImportResult>(`/api/admin/cups/${cup.id}/import/initial`,{
        method:"POST",
        body:JSON.stringify({proposal,import_matches:importSchedule && proposalMatches.length>0,fallback_date:startDate||null}),
      },token);

      goToCup(cup);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Importen kunde inte slutföras.";
      setError(cup ? `Cupen skapades som utkast men importen avbröts: ${detail}. Öppna cupen och kontrollera det som hann importeras.` : detail);
      if (cup) localStorage.setItem(CUP_KEY,String(cup.id));
      setBusy(false);
    }
  }

  if (!isOwner) return null;

  return <>
    <section className="cup-create-toolbar" aria-label="Cupåtgärder">
      <div>
        <span>CUPADMINISTRATION</span>
        <strong>Skapa en cup manuellt eller läs in ett befintligt underlag</strong>
      </div>
      <button type="button" onClick={openDialog}>+ Ny cup</button>
    </section>

    {open && <div className="cup-create-backdrop" role="presentation" onMouseDown={event => {
      if (event.target === event.currentTarget) closeDialog();
    }}>
      <section className="cup-create-dialog" role="dialog" aria-modal="true" aria-labelledby="cup-create-title" style={{maxWidth:900}}>
        <div className="cup-create-dialog__head">
          <div><span>NY CUP</span><h2 id="cup-create-title">Hur vill du starta?</h2></div>
          <button type="button" className="cup-create-close" onClick={closeDialog} aria-label="Stäng">×</button>
        </div>
        <p className="cup-create-lead">Cupen blir alltid ett utkast först. Foto/PDF-import sparar inget förrän du har granskat resultatet.</p>

        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:18}}>
          <button type="button" className={mode==="manual"?"":"is-secondary"} onClick={()=>{setMode("manual");setError("");}}>✍️ Skapa manuellt</button>
          <button type="button" className={mode==="import"?"":"is-secondary"} onClick={()=>{setMode("import");setError("");}}>📷 Importera bild / PDF</button>
        </div>

        {mode==="manual" ? <form onSubmit={createCup}>
          <label>Cupnamn<input autoFocus value={name} onChange={event => setName(event.target.value)} placeholder="Exempel: Höstcupen 2026" maxLength={120} required /></label>
          <div className="cup-create-dates">
            <label>Startdatum<input type="date" value={startDate} onChange={event => { const value=event.target.value; setStartDate(value); if(!endDate)setEndDate(value); }} /></label>
            <label>Slutdatum<input type="date" min={startDate || undefined} value={endDate} onChange={event => setEndDate(event.target.value)} /></label>
          </div>
          {error && <p className="cup-create-error" role="alert">{error}</p>}
          <div className="cup-create-actions"><button type="button" className="is-secondary" onClick={closeDialog} disabled={busy}>Avbryt</button><button type="submit" disabled={busy || !name.trim()}>{busy?"Skapar…":"Skapa cup"}</button></div>
        </form> : <div>
          {!proposal ? <>
            <label style={{display:"grid",gap:8,padding:18,border:"2px dashed currentColor",borderRadius:12,cursor:"pointer",textAlign:"center"}}>
              <strong>Släpp bilder/PDF här eller välj filer</strong>
              <span style={{fontSize:13,opacity:.8}}>PDF, TXT, PNG, JPG, JPEG eller WEBP · flera filer går bra</span>
              <input type="file" multiple accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,image/*,application/pdf,text/plain" onChange={event=>setFiles(Array.from(event.target.files || []))} />
            </label>
            {!!files.length && <div style={{marginTop:12}}><strong>{files.length} filer valda</strong><ul>{files.map(file=><li key={`${file.name}-${file.size}`}>{file.name}</li>)}</ul></div>}
            {error && <p className="cup-create-error" role="alert">{error}</p>}
            <div className="cup-create-actions"><button type="button" className="is-secondary" onClick={closeDialog} disabled={busy}>Avbryt</button><button type="button" disabled={busy||!files.length} onClick={()=>void analyzeFiles()}>{busy?"Läser underlaget…":"✨ Läs in underlaget"}</button></div>
          </> : <form onSubmit={createFromImport}>
            <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:8,marginBottom:14}}>
              <div><strong>{proposalTeams.length}</strong><small style={{display:"block"}}>Lag</small></div>
              <div><strong>{proposalGroups.length}</strong><small style={{display:"block"}}>Grupper</small></div>
              <div><strong>{proposalMatches.length}</strong><small style={{display:"block"}}>Matcher hittade</small></div>
              <div><strong>{(proposal.venues||[]).length}</strong><small style={{display:"block"}}>Planer</small></div>
            </div>
            <label>Cupnamn<input value={name} onChange={event=>setName(event.target.value)} required /></label>
            <div className="cup-create-dates"><label>Startdatum<input type="date" value={startDate} onChange={event=>setStartDate(event.target.value)} /></label><label>Slutdatum<input type="date" min={startDate||undefined} value={endDate} onChange={event=>setEndDate(event.target.value)} /></label></div>
            {proposal.location && <p><strong>Plats:</strong> {proposal.location}</p>}
            {!!proposalGroups.length && <p><strong>Grupper:</strong> {proposalGroups.join(", ")}</p>}
            {!!proposalTeams.length && <details open><summary><strong>Lag som kommer importeras ({proposalTeams.length})</strong></summary><ul>{proposalTeams.map((team,index)=><li key={`${team.name}-${index}`}>{team.name}{team.group_name?` — ${team.group_name}`:""}</li>)}</ul></details>}
            {!!(proposal.rules||[]).length && <details><summary><strong>Regler hittade ({proposal.rules!.length})</strong></summary><ul>{proposal.rules!.map((rule,index)=><li key={index}>{rule}</li>)}</ul></details>}
            {!!proposalMatches.length && <details open style={{marginTop:14}}>
              <summary><strong>Granska matchschema ({proposalMatches.length})</strong></summary>
              <p style={{fontSize:13}}>Kontrollera varje rad. Importen stoppas om ett lag, en grupp eller plan inte stämmer med det du godkänner.</p>
              <div style={{display:"grid",gap:8}}>{proposalMatches.map((match,index)=><div key={index} style={{display:"grid",gridTemplateColumns:"100px 1fr 1fr 1fr 1fr",gap:6,alignItems:"end"}}>
                <label>Tid<input value={match.time||""} onChange={event=>updateImportedMatch(index,"time",event.target.value)} /></label>
                <label>Grupp<input value={match.group_name||""} onChange={event=>updateImportedMatch(index,"group_name",event.target.value)} /></label>
                <label>Hemma<input value={match.home_team||""} onChange={event=>updateImportedMatch(index,"home_team",event.target.value)} /></label>
                <label>Borta<input value={match.away_team||""} onChange={event=>updateImportedMatch(index,"away_team",event.target.value)} /></label>
                <label>Plan<input value={match.venue||""} onChange={event=>updateImportedMatch(index,"venue",event.target.value)} /></label>
              </div>)}</div>
              <label style={{display:"flex",gap:10,alignItems:"center",marginTop:12}}><input type="checkbox" checked={importSchedule} onChange={event=>setImportSchedule(event.target.checked)} /> Använd det granskade matchprogrammet som cupens befintliga schema</label>
              <p style={{fontSize:13}}>Schemat låses som importerat underlag och publiceras inte automatiskt. Avmarkera om du bara vill spara avläsningen för senare.</p>
            </details>}
            {!!(proposal.playoff_matches||[]).length && <p style={{padding:10,border:"1px solid currentColor",borderRadius:8}}><strong>Slutspel hittat:</strong> {(proposal.playoff_matches||[]).length} matcher/källor. Slutspelsimport kopplas in i nästa block.</p>}
            {!!(proposal.warnings||[]).length && <div className="cup-create-error"><strong>Kontrollera innan du fortsätter</strong><ul>{proposal.warnings!.map((warning,index)=><li key={index}>{warning}</li>)}</ul></div>}
            {error && <p className="cup-create-error" role="alert">{error}</p>}
            <div className="cup-create-actions"><button type="button" className="is-secondary" disabled={busy} onClick={()=>{setProposal(null);setImportSchedule(false);setError("");}}>← Byt filer</button><button type="submit" disabled={busy||!name.trim()}>{busy?"Importerar…":"✓ Skapa cup från granskningen"}</button></div>
          </form>}
        </div>}
      </section>
    </div>}
  </>;
}