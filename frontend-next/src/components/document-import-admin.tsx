"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const API = CLIENT_API_BASE;

type ImportedTeam = { name:string; group_name?:string|null };
type ImportedMatch = {
  time?:string|null; venue?:string|null; group_name?:string|null;
  home_team?:string|null; away_team?:string|null; stage?:string|null; duration?:string|null;
};
type ImportProposal = {
  tournament_name?:string|null; start_date?:string|null; end_date?:string|null; source_name?:string|null;
  venues?:string[]; teams?:ImportedTeam[]; matches?:ImportedMatch[]; playoff_matches?:unknown[];
  rules?:string[]; rule_values?:Record<string,number|null>; warnings?:string[];
};
type ExistingGroup = { id:number; name:string };
type ExistingTeam = { id:number; name:string; group_id?:number|null };
type CreatedGroup = { id:number; name:string };
type CreatedTeam = { id:number; name:string; group_id?:number|null };
type SchedulePayload = { match_count:number };
type CupInfoPayload = { name:string; start_date?:string|null };
type VenuePayload = {
  rules:{pitch_count:number;first_match_time:string;latest_kickoff_time:string;synchronized_pitch_times:boolean;consider_pitch_travel:boolean};
  pitches:{pitch_number:number;name:string;address?:string|null}[];
  scheduled_count:number;
};
type RulesPayload = { scheduled_count:number; completed_count:number };

function normalize(value?:string|null) {
  return (value || "").trim().toLocaleLowerCase("sv");
}

function groupNames(teams:ImportedTeam[]) {
  return [...new Map(teams.map(team => (team.group_name || "").trim()).filter(Boolean).map(name => [normalize(name),name])).values()];
}

function compactRuleValues(values?:Record<string,number|null>) {
  return Object.fromEntries(Object.entries(values || {}).filter(([,value]) => value !== null && value !== undefined));
}

function defaultPitchName(pitch:{pitch_number:number;name:string}) {
  return !pitch.name.trim() || normalize(pitch.name) === normalize(`Plan ${pitch.pitch_number}`);
}

function friendlyAnalyzeError(message:string) {
  if (/HTTP Error 400|Bad Request/i.test(message)) {
    return "PDF:en kunde inte läsas av AI-tjänsten. Prova att exportera PDF:en på nytt, ladda upp färre sidor eller fotografera schemat som bild.";
  }
  return message;
}

async function api<T>(path:string, options:RequestInit, token:string):Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type","application/json");
  headers.set("Authorization",`Bearer ${token}`);
  const response = await fetch(`${API}${path}`,{...options,headers,cache:"no-store"});
  const payload = await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail || `API-fel ${response.status}`);
  return payload as T;
}

export default function DocumentImportAdmin({token,cupId,onImported}:{token:string;cupId:number;onImported?:()=>void|Promise<void>}) {
  const [files,setFiles] = useState<File[]>([]);
  const [proposal,setProposal] = useState<ImportProposal|null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const [stage,setStage] = useState("");
  const [importTeams,setImportTeams] = useState(true);
  const [importSchedule,setImportSchedule] = useState(true);
  const [importSetup,setImportSetup] = useState(true);
  const teams = proposal?.teams || [];
  const groups = useMemo(()=>groupNames(teams),[teams]);
  const matches = proposal?.matches || [];
  const ruleValues = useMemo(()=>compactRuleValues(proposal?.rule_values),[proposal?.rule_values]);

  function choose(event:ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files || []));
    setProposal(null);
    setError("");
    setMessage("");
  }

  async function analyze() {
    if(!files.length)return;
    setBusy(true); setError(""); setMessage(""); setStage("Läser underlaget…");
    try {
      const form = new FormData();
      files.forEach(file => form.append("files",file,file.name));
      const result = await api<ImportProposal>("/api/admin/cup-import/analyze",{method:"POST",body:form},token);
      setProposal(result);
      setImportSchedule(Boolean(result.matches?.length));
      setMessage("Underlaget är avläst. Granska sammanfattningen innan du sparar något till cupen.");
    } catch (err) {
      setError(friendlyAnalyzeError(err instanceof Error ? err.message : "Underlaget kunde inte läsas."));
    } finally {
      setBusy(false); setStage("");
    }
  }

  async function commit() {
    if(!proposal)return;
    setBusy(true); setError(""); setMessage(""); setStage("Kontrollerar befintlig cupdata…");
    const notes:string[] = [];
    try {
      const [cupinfo,groupPayload,teamPayload,schedule] = await Promise.all([
        api<CupInfoPayload>(`/api/admin/cups/${cupId}/cupinfo`,{},token),
        api<{groups:ExistingGroup[]}>(`/api/admin/cups/${cupId}/groups`,{},token),
        api<{teams:ExistingTeam[]}>(`/api/admin/cups/${cupId}/teams`,{},token),
        api<SchedulePayload>(`/api/admin/cups/${cupId}/schedule`,{},token),
      ]);
      const groupIds = new Map((groupPayload.groups || []).map(group => [normalize(group.name),group.id]));
      const existingTeams = new Map((teamPayload.teams || []).map(team => [normalize(team.name),team]));
      let createdGroups = 0, createdTeams = 0, assignedTeams = 0;

      if(importTeams) {
        setStage("Sparar saknade grupper och lag…");
        for (const groupName of groups) {
          const key = normalize(groupName);
          if(groupIds.has(key))continue;
          const created = await api<CreatedGroup>(`/api/admin/cups/${cupId}/groups`,{method:"POST",body:JSON.stringify({name:groupName})},token);
          groupIds.set(key,created.id);
          createdGroups += 1;
        }
        for (const row of teams) {
          const key = normalize(row.name);
          if(!key)continue;
          let team = existingTeams.get(key);
          if(!team) {
            team = await api<CreatedTeam>(`/api/admin/cups/${cupId}/teams`,{method:"POST",body:JSON.stringify({name:row.name})},token);
            existingTeams.set(key,team);
            createdTeams += 1;
          }
          const groupId = row.group_name ? groupIds.get(normalize(row.group_name)) : undefined;
          if(groupId && !team.group_id) {
            const saved = await api<CreatedTeam>(`/api/admin/cups/${cupId}/teams/${team.id}/group`,{method:"PUT",body:JSON.stringify({group_id:groupId})},token);
            existingTeams.set(key,saved);
            assignedTeams += 1;
          } else if(groupId && team.group_id && team.group_id !== groupId) {
            notes.push(`${row.name} hade redan en annan grupp och flyttades inte.`);
          }
        }
      }

      if(importSetup) {
        if(proposal.venues?.length) {
          setStage("Fyller tomma planuppgifter…");
          let venues = await api<VenuePayload>(`/api/admin/cups/${cupId}/venues`,{},token);
          if(venues.scheduled_count > 0) {
            notes.push("Planer hoppades över eftersom cupen redan har schemalagda matcher.");
          } else {
            const pitchCount = Math.max(Number(venues.rules.pitch_count || 1),proposal.venues.length);
            if(pitchCount !== venues.rules.pitch_count) {
              venues = await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/rules`,{method:"PUT",body:JSON.stringify({...venues.rules,pitch_count: pitchCount})},token);
            }
            for (let index=0; index<proposal.venues.length; index += 1) {
              const pitchNumber = index + 1;
              const current = venues.pitches.find(pitch => pitch.pitch_number === pitchNumber);
              if(current && !defaultPitchName(current)) {
                notes.push(`Plan ${pitchNumber} hade redan namnet ${current.name} och skrevs inte över.`);
                continue;
              }
              await api<VenuePayload>(`/api/admin/cups/${cupId}/venues/pitches/${pitchNumber}`,{method:"PUT",body:JSON.stringify({name:proposal.venues[index]})},token);
            }
          }
        }
        if(Object.keys(ruleValues).length) {
          setStage("Fyller regelvärden…");
          const currentRules = await api<RulesPayload>(`/api/admin/cups/${cupId}/rules`,{},token);
          if(Number(currentRules.completed_count || 0) > 0) {
            notes.push("Regelvärden hoppades över eftersom cupen redan har färdigspelade matcher.");
          } else {
            await api(`/api/admin/cups/${cupId}/rules`,{method:"PUT",body:JSON.stringify(ruleValues)},token);
          }
        }
      }

      setStage("Sparar foto/PDF-underlaget för fortsatta granskningssteg…");
      const fallbackDate = proposal.start_date || cupinfo.start_date || null;
      const canImportMatches = importSchedule && matches.length > 0 && schedule.match_count === 0 && Boolean(fallbackDate);
      if(importSchedule && matches.length > 0 && schedule.match_count > 0) {
        notes.push("Matchprogrammet sparades som underlag men importerades inte eftersom cupen redan har matcher.");
      } else if(importSchedule && matches.length > 0 && !fallbackDate) {
        notes.push("Matchprogrammet sparades som underlag men importerades inte eftersom cupdatum saknas.");
      }
      await api(`/api/admin/cups/${cupId}/import/initial`,{
        method:"POST",
        body:JSON.stringify({proposal,import_matches:canImportMatches,fallback_date:fallbackDate}),
      },token);
      const summary = [
        importTeams ? `${createdTeams} nya lag, ${createdGroups} nya grupper, ${assignedTeams} gruppkopplingar` : "lag/grupper hoppades över",
        canImportMatches ? `${matches.length} matcher importerades` : "matchprogrammet sparades för granskning",
      ];
      setMessage(`${summary.join(" · ")}.${notes.length ? ` Kontroll: ${notes.join(" ")}` : ""}`);
      setProposal(null);
      setFiles([]);
      await onImported?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Foto/PDF-importen kunde inte sparas.");
    } finally {
      setBusy(false); setStage("");
    }
  }

  return <section className="admin-panel admin-teams import-update-card" id="import">
    <div className="admin-panel__top"><span>FOTO/PDF · EFTERHANDSIMPORT</span><strong>GRANSKA FÖRST</strong></div>
    <div className="admin-cupinfo__head"><div><h2>Läs in foto/PDF till aktiv cup</h2><p>För cuper som skapats manuellt men där underlaget ska läsas in i efterhand. CupNavi fyller luckor och sparar originalunderlaget för slutspel, plantider och fortsatt granskning.</p></div><span className="admin-lock">SKRIVER INTE ÖVER</span></div>
    <div className="admin-team-editor import-file-picker">
      <label><span>Foto eller PDF</span><input type="file" multiple accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,image/*,application/pdf,text/plain" onChange={choose} disabled={busy}/></label>
      <small>{files.length ? `${files.length} filer valda: ${files.map(file=>file.name).join(", ")}` : "Välj samma typ av cupunderlag som vid ny cup. Du får granska resultatet innan något sparas."}</small>
      <button type="button" disabled={busy||!files.length} onClick={()=>void analyze()}>{busy&&stage?stage:"Läs in underlaget"}</button>
    </div>
    {(error||message)&&<div className="admin-code-placeholder" style={{marginTop:16}} role={error?"alert":undefined}><b>{error?"Fel":"Klart"}</b> · {error||message}</div>}
    {proposal&&<>
      <div className="cup-import-stats" style={{marginTop:16}}>
        <div><strong>{teams.length}</strong><small>Lag</small></div>
        <div><strong>{groups.length}</strong><small>Grupper</small></div>
        <div><strong>{matches.length}</strong><small>Matcher</small></div>
        <div><strong>{(proposal.venues||[]).length}</strong><small>Planer</small></div>
      </div>
      <div className="admin-team-editor" style={{marginTop:14}}>
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={importTeams} onChange={event=>setImportTeams(event.target.checked)}/> Lägg in saknade lag och grupper</label>
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={importSchedule} onChange={event=>setImportSchedule(event.target.checked)} disabled={!matches.length}/> Importera matchprogram om cupen saknar matcher</label>
        <label style={{display:"flex",alignItems:"center",gap:10}}><input type="checkbox" checked={importSetup} onChange={event=>setImportSetup(event.target.checked)}/> Fyll tomma planer och regelvärden</label>
      </div>
      {!!proposal.warnings?.length&&<details className="cup-import-notes" style={{marginTop:12}}><summary>Noteringar från avläsningen ({proposal.warnings.length})</summary><ul>{proposal.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></details>}
      <div className="admin-form-footer"><span>{stage || "Befintlig cupdata bevaras. Osäkra delar får granskas i importöversikten efteråt."}</span><button type="button" disabled={busy} onClick={()=>void commit()}>{busy?"Sparar…":"Spara till aktiv cup"}</button></div>
    </>}
  </section>;
}
