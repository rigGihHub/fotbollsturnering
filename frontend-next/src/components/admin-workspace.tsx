"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import VenueAdmin from "./venue-admin";
import RulesAdmin from "./rules-admin";
import ScheduleAdmin from "./schedule-admin";
import RefereeAdmin from "./referee-admin";
import PlayoffAdmin from "./playoff-admin";

const API_BASE = (process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "cupnavi_admin_session_v629";

const nav = [
  ["Översikt", "#overview"], ["Cupinfo", "#cupinfo"], ["Lag", "#teams"], ["Grupper", "#groups"],
  ["Planer & tider", "#venues"], ["Regler", "#rules"], ["Schema", "#schedule"], ["Domare", "#referees"],
  ["Slutspel", "#playoffs"], ["Publicering", "#publish"], ["Matchrapportering", "#reporting"], ["Import", "#import"], ["PDF & export", "#export"]
];

const modules = [
  ["publish","10","Publicering","Förhandsgranska cupen och publicera först när checklistan är klar."],
  ["reporting","11","Matchrapportering","Resultat, målskyttar, assist och kort när statistiken är aktiverad."],
  ["import","12","Import","Läs in tidigare cupprogram från dokument eller flera bilder utan att skriva över data tyst."],
  ["export","13","PDF & export","Förhandsgranska, skapa och ladda ned cupens PDF från samma flöde."]
];

type Account = { id:number; email:string; display_name?:string|null };
type Cup = { id:number; name:string; public_slug?:string|null; start_date?:string|null; end_date?:string|null; is_published?:number|boolean; role:string };
type CupInfo = {
  id:number; public_slug?:string|null; is_published?:number|boolean;
  name:string; start_date?:string|null; end_date?:string|null; organizer?:string|null;
  arena_address?:string|null; organizer_phone?:string|null; feedback_email?:string|null;
  public_information?:string|null;
};
type SessionPayload = { account:Account; cups:Cup[]; token?:string };
type Team = { id:number; tournament_id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null };
type Group = { id:number; tournament_id:number; name:string; age_class?:string|null; team_count:number };
const emptyTeam = {name:"",age_class:"",primary_color:"#111827",secondary_color:"#FFFFFF"};
const emptyGroup = {name:"",age_class:""};

async function request<T>(path:string, options:RequestInit = {}, token?:string|null):Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache:"no-store" });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : `API-fel ${response.status}`;
    throw new Error(detail);
  }
  return payload as T;
}

function cleanCupInfo(value:CupInfo):CupInfo {
  return {
    ...value,
    name:value.name || "",
    start_date:value.start_date || "",
    end_date:value.end_date || "",
    organizer:value.organizer || "",
    arena_address:value.arena_address || "",
    organizer_phone:value.organizer_phone || "",
    feedback_email:value.feedback_email || "",
    public_information:value.public_information || "",
  };
}

export default function AdminWorkspace() {
  const [token,setToken] = useState<string|null>(null);
  const [account,setAccount] = useState<Account|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [cupId,setCupId] = useState<number|null>(null);
  const [cupinfo,setCupinfo] = useState<CupInfo|null>(null);
  const [teams,setTeams] = useState<Team[]>([]);
  const [groups,setGroups] = useState<Group[]>([]);
  const [teamDraft,setTeamDraft] = useState(emptyTeam);
  const [groupDraft,setGroupDraft] = useState(emptyGroup);
  const [editingTeam,setEditingTeam] = useState<number|null>(null);
  const [editingGroup,setEditingGroup] = useState<number|null>(null);
  const [email,setEmail] = useState("");
  const [password,setPassword] = useState("");
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState("");
  const [error,setError] = useState("");

  const activeCup = useMemo(() => cups.find(cup => cup.id === cupId) || null,[cups,cupId]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null); setAccount(null); setCups([]); setCupId(null); setCupinfo(null); setTeams([]); setGroups([]);
    setPassword(""); setMessage(""); setError("");
  },[]);

  const loadCupInfo = useCallback(async (nextToken:string, nextCupId:number) => {
    const [data,teamData,groupData] = await Promise.all([
      request<CupInfo>(`/api/admin/cups/${nextCupId}/cupinfo`,{},nextToken),
      request<{teams:Team[]}>(`/api/admin/cups/${nextCupId}/teams`,{},nextToken),
      request<{groups:Group[]}>(`/api/admin/cups/${nextCupId}/groups`,{},nextToken),
    ]);
    setCupinfo(cleanCupInfo(data)); setTeams(teamData.teams || []); setGroups(groupData.groups || []);
    setEditingTeam(null); setTeamDraft(emptyTeam); setEditingGroup(null); setGroupDraft(emptyGroup);
  },[]);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    setBusy(true);
    request<SessionPayload>("/api/admin/session",{},stored)
      .then(async data => {
        setToken(stored); setAccount(data.account); setCups(data.cups || []);
        const first = data.cups?.[0];
        if (first) { setCupId(first.id); await loadCupInfo(stored,first.id); }
      })
      .catch(() => logout())
      .finally(() => setBusy(false));
  },[loadCupInfo,logout]);

  async function login(event:FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const data = await request<SessionPayload>("/api/admin/session",{method:"POST",body:JSON.stringify({email,password})});
      if (!data.token) throw new Error("API:t returnerade ingen session.");
      localStorage.setItem(TOKEN_KEY,data.token);
      setToken(data.token); setAccount(data.account); setCups(data.cups || []); setPassword("");
      const first = data.cups?.[0];
      if (first) { setCupId(first.id); await loadCupInfo(data.token,first.id); }
      else setMessage("Kontot är giltigt men är inte kopplat till någon cup ännu.");
    } catch (err) { setError(err instanceof Error ? err.message : "Inloggningen misslyckades."); }
    finally { setBusy(false); }
  }

  async function changeCup(nextId:number) {
    if (!token) return;
    setCupId(nextId); setBusy(true); setError(""); setMessage("");
    try { await loadCupInfo(token,nextId); }
    catch (err) { setError(err instanceof Error ? err.message : "Cupen kunde inte hämtas."); }
    finally { setBusy(false); }
  }

  async function saveCupInfo(event:FormEvent) {
    event.preventDefault();
    if (!token || !cupId || !cupinfo) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved = await request<CupInfo>(`/api/admin/cups/${cupId}/cupinfo`,{
        method:"PUT",
        body:JSON.stringify({name:cupinfo.name,start_date:cupinfo.start_date || null,end_date:cupinfo.end_date || null,organizer:cupinfo.organizer || null,arena_address:cupinfo.arena_address || null,organizer_phone:cupinfo.organizer_phone || null,feedback_email:cupinfo.feedback_email || null,public_information:cupinfo.public_information || null})
      },token);
      const normalized = cleanCupInfo(saved);
      setCupinfo(normalized);
      setCups(current => current.map(cup => cup.id === cupId ? {...cup,name:normalized.name,start_date:normalized.start_date,end_date:normalized.end_date,public_slug:normalized.public_slug,is_published:normalized.is_published} : cup));
      setMessage("Cupinfo sparad i CupNavis riktiga databas.");
    } catch (err) { setError(err instanceof Error ? err.message : "Cupinfo kunde inte sparas."); }
    finally { setBusy(false); }
  }

  function beginTeamEdit(team:Team) {
    setEditingTeam(team.id);
    setTeamDraft({name:team.name,age_class:team.age_class || "",primary_color:team.primary_color || "#111827",secondary_color:team.secondary_color || "#FFFFFF"});
    setError(""); setMessage("");
  }
  function cancelTeamEdit() { setEditingTeam(null); setTeamDraft(emptyTeam); }

  async function saveTeam(event:FormEvent) {
    event.preventDefault();
    if (!token || !cupId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const path = editingTeam ? `/api/admin/cups/${cupId}/teams/${editingTeam}` : `/api/admin/cups/${cupId}/teams`;
      const saved = await request<Team>(path,{method:editingTeam?"PUT":"POST",body:JSON.stringify(teamDraft)},token);
      setTeams(current => editingTeam ? current.map(team=>team.id===saved.id?saved:team).sort((a,b)=>a.name.localeCompare(b.name,"sv")) : [...current,saved].sort((a,b)=>a.name.localeCompare(b.name,"sv")));
      setMessage(editingTeam ? "Laget har uppdaterats." : "Laget har lagts till.");
      cancelTeamEdit();
    } catch (err) { setError(err instanceof Error ? err.message : "Laget kunde inte sparas."); }
    finally { setBusy(false); }
  }

  async function removeTeam(team:Team) {
    if (!token || !cupId || !window.confirm(`Ta bort ${team.name}? Åtgärden går inte att ångra.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await request(`/api/admin/cups/${cupId}/teams/${team.id}`,{method:"DELETE"},token);
      setTeams(current=>current.filter(item=>item.id!==team.id));
      if (editingTeam===team.id) cancelTeamEdit();
      setMessage(`${team.name} har tagits bort.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Laget kunde inte tas bort."); }
    finally { setBusy(false); }
  }

  function beginGroupEdit(group:Group) {
    setEditingGroup(group.id); setGroupDraft({name:group.name,age_class:group.age_class || ""}); setError(""); setMessage("");
  }
  function cancelGroupEdit() { setEditingGroup(null); setGroupDraft(emptyGroup); }

  async function saveGroup(event:FormEvent) {
    event.preventDefault();
    if (!token || !cupId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const path = editingGroup ? `/api/admin/cups/${cupId}/groups/${editingGroup}` : `/api/admin/cups/${cupId}/groups`;
      const saved = await request<Group>(path,{method:editingGroup?"PUT":"POST",body:JSON.stringify(groupDraft)},token);
      setGroups(current => editingGroup ? current.map(group=>group.id===saved.id?saved:group).sort((a,b)=>a.name.localeCompare(b.name,"sv")) : [...current,saved].sort((a,b)=>a.name.localeCompare(b.name,"sv")));
      setMessage(editingGroup ? "Gruppen har uppdaterats." : "Gruppen har skapats.");
      cancelGroupEdit();
    } catch (err) { setError(err instanceof Error ? err.message : "Gruppen kunde inte sparas."); }
    finally { setBusy(false); }
  }

  async function removeGroup(group:Group) {
    if (!token || !cupId || !window.confirm(`Ta bort ${group.name}? Gruppen måste vara tom och oanvänd i schemat.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await request(`/api/admin/cups/${cupId}/groups/${group.id}`,{method:"DELETE"},token);
      setGroups(current=>current.filter(item=>item.id!==group.id));
      if (editingGroup===group.id) cancelGroupEdit();
      setMessage(`${group.name} har tagits bort.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Gruppen kunde inte tas bort."); }
    finally { setBusy(false); }
  }

  async function assignGroup(team:Team, groupId:number|null) {
    if (!token || !cupId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved = await request<Team>(`/api/admin/cups/${cupId}/teams/${team.id}/group`,{method:"PUT",body:JSON.stringify({group_id:groupId})},token);
      setTeams(current=>current.map(item=>item.id===saved.id?saved:item));
      const groupData = await request<{groups:Group[]}>(`/api/admin/cups/${cupId}/groups`,{},token);
      setGroups(groupData.groups || []);
      setMessage(groupId ? `${team.name} har flyttats till ${groups.find(group=>group.id===groupId)?.name || "gruppen"}.` : `${team.name} är nu ogrupperat.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Gruppindelningen kunde inte sparas."); }
    finally { setBusy(false); }
  }

  if (!account) {
    return <main className="admin-main" style={{maxWidth:720,margin:"0 auto"}}>
      <header className="admin-pagehead"><div><p className="kicker">CN//ADMIN</p><h1>Logga in</h1><p>Använd samma arrangörskonto som i CupNavi.</p></div></header>
      <form className="admin-panel admin-cupinfo" onSubmit={login}>
        <div className="admin-panel__top"><span>ARRANGÖR</span><strong>RIKTIG BEHÖRIGHET</strong></div>
        <h2>Cupadministration</h2>
        <div className="admin-form-grid">
          <label>E-post<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required /></label>
          <label>Lösenord<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label>
        </div>
        <div className="admin-form-footer"><span>{error || "Inloggningen verifieras mot befintliga arrangörskonton."}</span><button type="submit" disabled={busy}>{busy?"Kontrollerar…":"Logga in"}</button></div>
      </form>
    </main>;
  }

  const publicCup = activeCup?.public_slug ? `/cup/${activeCup.public_slug}` : null;
  const groupedTeams = teams.filter(team=>team.group_id != null).length;
  const checks = [["Cupinfo",cupinfo?.name ? "Påbörjad":"Ej klar"],["Lag",teams.length?`${teams.length} registrerade`:"Ej klar"],["Grupper",groups.length?`${groups.length} grupper · ${groupedTeams}/${teams.length} lag`:"Ej klar"],["Schema","Riktig modul inkopplad"],["Publicering",activeCup?.is_published ? "Publicerad":"Ej klar"]];

  return <main className="admin-workspace">
    <aside className="admin-sidebar">
      <div className="admin-sidebar__cup"><span>AKTIV CUP</span><strong>{activeCup?.name || "Ingen cup"}</strong><small>{activeCup?.start_date || "Datum saknas"}</small></div>
      {cups.length > 1 && <label style={{display:"grid",gap:6,padding:"14px 10px"}}>Byt cup<select value={cupId || ""} onChange={e=>changeCup(Number(e.target.value))}>{cups.map(cup=><option key={cup.id} value={cup.id}>{cup.name}</option>)}</select></label>}
      <nav aria-label="Cupadministration">{nav.map(([item,href],index)=><a className={index===0?"is-active":""} href={href} key={item}><span>{String(index+1).padStart(2,"0")}</span>{item}</a>)}</nav>
      {publicCup && <a className="admin-public-link" href={publicCup}>Visa publik cup ↗</a>}
      <button className="admin-public-link" type="button" onClick={logout}>Logga ut</button>
    </aside>

    <section className="admin-main" id="overview">
      <header className="admin-pagehead"><div><p className="kicker">CN//ADMIN</p><h1>Cupöversikt</h1><p>{account.display_name || account.email} · {activeCup?.role || "arrangör"}</p></div><div className="admin-pagehead__actions"><span className="admin-draft">{activeCup?.is_published?"PUBLICERAD":"UTKAST"}</span>{publicCup&&<a href={publicCup}>Förhandsgranska</a>}</div></header>
      {(error||message) && <section className="admin-panel" style={{marginBottom:14}}><strong>{error?"Kunde inte genomföra ändringen":"Klart"}</strong><p>{error||message}</p></section>}
      <section className="admin-dashboard-grid">
        <article className="admin-panel admin-panel--status"><div className="admin-panel__top"><span>PUBLICERINGSSTATUS</span><strong>{activeCup?.is_published?"LIVE":"ARBETE PÅGÅR"}</strong></div><h2>{activeCup?.is_published?"Cupen är publicerad":"Cupen är inte publicerad än"}</h2><div className="admin-checks">{checks.map(([name,status],i)=><div key={name}><span className={i===0?"is-progress":""}>{i===0?"◐":"○"}</span><strong>{name}</strong><small>{status}</small></div>)}</div></article>
        <article className="admin-panel admin-panel--codes"><div className="admin-panel__top"><span>BEHÖRIGHET</span><strong>SERVERVERIFIERAD</strong></div><h2>Åtkomst</h2><p>Du är inloggad med CupNavis befintliga arrangörskonto. Cupåtkomst hämtas från tournament_members.</p><div className="admin-code-placeholder">Konto <b>{account.email}</b></div><div className="admin-code-placeholder">Roll <b>{activeCup?.role || "—"}</b></div></article>
      </section>

      <form className="admin-panel admin-cupinfo" id="cupinfo" onSubmit={saveCupInfo}>
        <div className="admin-panel__top"><span>02 / CUPINFO</span><strong>{busy?"ARBETAR":"SKRIVANDE API AKTIVT"}</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Grunduppgifter</h2><p>Fälten läses från och sparas direkt till den valda cupens befintliga tournament-post.</p></div><span className="admin-lock">BEHÖRIG</span></div>
        {cupinfo ? <>
          <div className="admin-form-grid">
            <label>Cupnamn<input value={cupinfo.name} onChange={e=>setCupinfo({...cupinfo,name:e.target.value})} required /></label>
            <label>Startdatum<input type="date" value={cupinfo.start_date || ""} onChange={e=>setCupinfo({...cupinfo,start_date:e.target.value})} /></label>
            <label>Slutdatum<input type="date" value={cupinfo.end_date || ""} onChange={e=>setCupinfo({...cupinfo,end_date:e.target.value})} /></label>
            <label>Arrangör<input value={cupinfo.organizer || ""} onChange={e=>setCupinfo({...cupinfo,organizer:e.target.value})} /></label>
            <label>Anläggning / adress<input value={cupinfo.arena_address || ""} onChange={e=>setCupinfo({...cupinfo,arena_address:e.target.value})} /></label>
            <label>Telefon<input value={cupinfo.organizer_phone || ""} onChange={e=>setCupinfo({...cupinfo,organizer_phone:e.target.value})} /></label>
            <label>Kontakt-e-post<input type="email" value={cupinfo.feedback_email || ""} onChange={e=>setCupinfo({...cupinfo,feedback_email:e.target.value})} /></label>
            <label style={{gridColumn:"1 / -1"}}>Publik information<textarea rows={5} value={cupinfo.public_information || ""} onChange={e=>setCupinfo({...cupinfo,public_information:e.target.value})} /></label>
          </div>
          <div className="admin-form-footer"><span>{message || "Ändringar blir publika enligt cupens vanliga publiceringsstatus."}</span><button type="submit" disabled={busy || !cupinfo.name.trim()}>{busy?"Sparar…":"Spara Cupinfo"}</button></div>
        </> : <p>{busy?"Hämtar Cupinfo…":"Ingen Cupinfo tillgänglig."}</p>}
      </form>

      <section className="admin-panel admin-teams" id="teams">
        <div className="admin-panel__top"><span>03 / LAG</span><strong>{teams.length} REGISTRERADE</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Lag</h2><p>Skapa lag och håll lagnamn, klass och matchställ uppdaterade. Alla ändringar sparas direkt i cupens databas.</p></div><span className="admin-lock">CRUD AKTIVT</span></div>
        <form onSubmit={saveTeam} className="admin-team-editor">
          <div className="admin-form-grid">
            <label>Lagnamn<input value={teamDraft.name} onChange={e=>setTeamDraft({...teamDraft,name:e.target.value})} required placeholder="Exempel: ÖSK P2014 Svart" /></label>
            <label>Klass<input value={teamDraft.age_class} onChange={e=>setTeamDraft({...teamDraft,age_class:e.target.value})} placeholder="Exempel: P2014" /></label>
            <label>Primär färg<span className="admin-color-input"><input type="color" value={teamDraft.primary_color} onChange={e=>setTeamDraft({...teamDraft,primary_color:e.target.value})} /><code>{teamDraft.primary_color}</code></span></label>
            <label>Sekundär färg<span className="admin-color-input"><input type="color" value={teamDraft.secondary_color} onChange={e=>setTeamDraft({...teamDraft,secondary_color:e.target.value})} /><code>{teamDraft.secondary_color}</code></span></label>
          </div>
          <div className="admin-form-footer"><span>{editingTeam?"Du redigerar ett befintligt lag.":"Lägg till ett lag i den aktiva cupen."}</span><div className="admin-team-actions">{editingTeam&&<button type="button" onClick={cancelTeamEdit}>Avbryt</button>}<button type="submit" disabled={busy||!teamDraft.name.trim()}>{busy?"Sparar…":editingTeam?"Spara lag":"Lägg till lag"}</button></div></div>
        </form>
        <div className="admin-team-list">
          {teams.length ? teams.map(team=><article key={team.id} className={editingTeam===team.id?"is-editing":""}>
            <span className="admin-team-shirt" style={{background:`linear-gradient(135deg,${team.primary_color||"#111827"} 0 50%,${team.secondary_color||"#FFFFFF"} 50%)`}} aria-hidden="true" />
            <div><strong>{team.name}</strong><small>{team.age_class||"Klass saknas"}{team.group_id?` · ${groups.find(group=>group.id===team.group_id)?.name || `Grupp ${team.group_id}`}`:" · Ej gruppindelat"}</small></div>
            <div className="admin-team-actions"><button type="button" onClick={()=>beginTeamEdit(team)}>Redigera</button><button className="is-danger" type="button" onClick={()=>removeTeam(team)}>Ta bort</button></div>
          </article>) : <div className="admin-empty"><strong>Inga lag ännu</strong><span>Lägg till det första laget ovan.</span></div>}
        </div>
      </section>

      <section className="admin-panel admin-teams" id="groups">
        <div className="admin-panel__top"><span>04 / GRUPPER</span><strong>{groups.length} GRUPPER · {groupedTeams}/{teams.length} LAG</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Gruppindelning</h2><p>Skapa grupper och placera varje lag. Flyttar sparas direkt och används av tabeller och kommande schemagenerering.</p></div><span className="admin-lock">CRUD AKTIVT</span></div>
        <form onSubmit={saveGroup} className="admin-team-editor">
          <div className="admin-form-grid">
            <label>Gruppnamn<input value={groupDraft.name} onChange={e=>setGroupDraft({...groupDraft,name:e.target.value})} required placeholder="Exempel: Grupp A" /></label>
            <label>Klass<input value={groupDraft.age_class} onChange={e=>setGroupDraft({...groupDraft,age_class:e.target.value})} placeholder="Exempel: P2014" /></label>
          </div>
          <div className="admin-form-footer"><span>{editingGroup?"Du redigerar en befintlig grupp.":"Skapa en grupp i den aktiva cupen."}</span><div className="admin-team-actions">{editingGroup&&<button type="button" onClick={cancelGroupEdit}>Avbryt</button>}<button type="submit" disabled={busy||!groupDraft.name.trim()}>{busy?"Sparar…":editingGroup?"Spara grupp":"Skapa grupp"}</button></div></div>
        </form>
        <div className="admin-team-list">
          {groups.length ? groups.map(group=><article key={group.id} className={editingGroup===group.id?"is-editing":""}>
            <div><strong>{group.name}</strong><small>{group.age_class||"Ingen klass"} · {group.team_count} lag</small></div>
            <div className="admin-team-actions"><button type="button" onClick={()=>beginGroupEdit(group)}>Redigera</button><button className="is-danger" type="button" onClick={()=>removeGroup(group)} disabled={group.team_count>0}>Ta bort</button></div>
          </article>) : <div className="admin-empty"><strong>Inga grupper ännu</strong><span>Skapa den första gruppen ovan.</span></div>}
        </div>
        <div className="admin-team-list" style={{marginTop:18}}>
          {teams.map(team=><article key={`group-team-${team.id}`}>
            <div><strong>{team.name}</strong><small>{team.age_class||"Klass saknas"}</small></div>
            <label style={{marginLeft:"auto"}}>Grupp<select value={team.group_id ?? ""} disabled={busy} onChange={e=>assignGroup(team,e.target.value?Number(e.target.value):null)}><option value="">Ej gruppindelat</option>{groups.map(group=><option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
          </article>)}
        </div>
      </section>

      {token && cupId && <VenueAdmin token={token} cupId={cupId} />}
      {token && cupId && <RulesAdmin token={token} cupId={cupId} />}
      {token && cupId && <ScheduleAdmin token={token} cupId={cupId} />}
      {token && cupId && <RefereeAdmin token={token} cupId={cupId} />}
      {token && cupId && <PlayoffAdmin token={token} cupId={cupId} />}

      <section className="admin-module-grid" aria-label="Cupens arbetsflöde">{modules.map(([id,n,title,text])=><article className="admin-panel admin-module-card" id={id} key={id}><div className="admin-panel__top"><span>{n} / MODUL</span><strong>FÖRBEREDD</strong></div><h2>{title}</h2><p>{text}</p><button disabled>Öppna när datalagret är inkopplat</button></article>)}</section>
    </section>
  </main>;
}