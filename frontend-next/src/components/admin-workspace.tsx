"use client";

import { CSSProperties, Fragment, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import VenueAdmin from "./venue-admin";
import RulesAdmin from "./rules-admin";
import ScheduleAdmin from "./schedule-admin";
import RefereeAdmin from "./referee-admin";
import PlayoffAdmin from "./playoff-admin";
import ExportAdmin from "./export-admin";
import { CLIENT_API_BASE } from "../lib/client-api";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";
const IMPORT_WELCOME_KEY = "cupnavi_import_welcome_v1";

const nav = [
  ["Översikt", "#overview"], ["Cupinfo", "#cupinfo"], ["Lag", "#teams"], ["Grupper", "#groups"],
  ["Planer & tider", "#venues"], ["Regler", "#rules"], ["Schema", "#schedule"], ["Domare", "#referees"],
  ["Slutspel", "#playoffs"], ["Publicering", "#publish"], ["Matchrapportering", "#reporting"], ["Import", "#import"], ["PDF & export", "#export"]
];
const adminPhaseStarts:Record<number,string>={0:"Överblick",1:"Grundarbete",6:"Matchplanering",9:"Genomförande",11:"Verktyg"};

type Account = { id:number; email:string; display_name?:string|null; role?:string|null; is_owner?:boolean };
type Cup = { id:number; name:string; public_slug?:string|null; start_date?:string|null; end_date?:string|null; is_published?:number|boolean; role:string };
type TrashedCup = Cup & { trashed_at?:string|null };
type CupInfo = {
  id:number; public_slug?:string|null; is_published?:number|boolean;
  name:string; start_date?:string|null; end_date?:string|null; organizer?:string|null;
  arena_address?:string|null; organizer_phone?:string|null; feedback_email?:string|null;
  public_information?:string|null;
};
type SessionPayload = { account:Account; cups:Cup[]; token?:string };
type AdminStep = "overview"|"cupinfo"|"teams"|"groups"|"venues"|"rules"|"schedule"|"referees"|"playoffs"|"publish"|"reporting"|"import"|"export";
type DeleteCupPayload = { deleted:boolean; recoverable:boolean; cup:Cup; cups:Cup[] };
type RestoreCupPayload = { restored:boolean; cup:Cup; cups:Cup[]; trash:TrashedCup[] };
type ApiStatus = "checking" | "online" | "offline";
type KitPattern = "Helfärgad"|"Vertikala ränder"|"Horisontella ränder"|"Rutigt"|"Delad";
type Team = { id:number; tournament_id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null; home_pattern?:KitPattern|null; home_color_2?:string|null; away_pattern?:KitPattern|null; away_color_2?:string|null; logo_url?:string|null; logo_source_url?:string|null };
type Group = { id:number; tournament_id:number; name:string; age_class?:string|null; team_count:number };
type ImportWelcome = { cupId:number; cupName:string; teams:number; groups:number; matches:number; venues:number };
type KitCandidate = {name:string;location:string;country:string;source_url:string;reason:string;confidence:string};
type KitSuggestion = {found:boolean;confidence:"low"|"medium"|"high";reason:string;club_match:string;identity_status:string;home_verified:boolean;away_verified:boolean;home_pattern:KitPattern;home_color_1:string;home_color_2:string;away_pattern:KitPattern;away_color_1:string;away_color_2:string;home_evidence:string;away_evidence:string;home_sources:string[];away_sources:string[];candidate_matches:KitCandidate[];logo_url:string;logo_source_url:string;logo_verified:boolean};
const emptyTeam = {name:"",age_class:"",primary_color:"#111827",secondary_color:"#FFFFFF",home_pattern:"Helfärgad" as KitPattern,home_color_2:"#FFFFFF",away_pattern:"Helfärgad" as KitPattern,away_color_2:"#111827",logo_url:"",logo_source_url:""};
const emptyGroup = {name:"",age_class:""};
const kitPatterns:KitPattern[]=["Helfärgad","Vertikala ränder","Horisontella ränder","Rutigt","Delad"];
const standardKitColors=[
  {name:"Vit",value:"#FFFFFF"},{name:"Svart",value:"#111827"},{name:"Röd",value:"#D72638"},
  {name:"Mörkblå",value:"#12355B"},{name:"Blå",value:"#246BCE"},{name:"Ljusblå",value:"#68B7E8"},
  {name:"Grön",value:"#238636"},{name:"Gul",value:"#F4C430"},{name:"Orange",value:"#F28C28"},
  {name:"Lila",value:"#713E8A"},{name:"Rosa",value:"#E56B9F"},{name:"Grå",value:"#7A8588"},
];
function kitBackground(pattern:KitPattern,c1:string,c2:string){
  if(pattern==="Vertikala ränder")return `repeating-linear-gradient(90deg,${c1} 0 8px,${c2} 8px 16px)`;
  if(pattern==="Horisontella ränder")return `repeating-linear-gradient(0deg,${c1} 0 8px,${c2} 8px 16px)`;
  if(pattern==="Rutigt")return `conic-gradient(${c1} 25%,${c2} 0 50%,${c1} 0 75%,${c2} 0) 0 0/16px 16px`;
  if(pattern==="Delad")return `linear-gradient(90deg,${c1} 0 50%,${c2} 50%)`;
  return c1;
}
function StandardKitColor({value,onChange,label}:{value:string;onChange:(value:string)=>void;label:string}){
  return <div className="admin-kit-palette" role="group" aria-label={label}>{standardKitColors.map(color=><button key={color.value} type="button" className={value.toUpperCase()===color.value?"is-selected":""} style={{"--choice-color":color.value} as CSSProperties} title={color.name} aria-label={color.name} aria-pressed={value.toUpperCase()===color.value} onClick={()=>onChange(color.value)}><span aria-hidden="true"/></button>)}</div>;
}

class ApiError extends Error {
  status:number;
  constructor(status:number,message:string){ super(message); this.name="ApiError"; this.status=status; }
}

async function request<T>(path:string, options:RequestInit = {}, token?:string|null):Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache:"no-store" });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const serverDetail = payload && typeof payload.detail === "string" ? payload.detail : "";
    const detail = response.status === 401 ? "Sessionen är inte längre giltig. Logga in igen."
      : response.status === 429 ? "För många försök. Vänta en stund innan du provar igen."
      : response.status === 503 ? "CupNavi-servern är tillfälligt inte redo. Försök igen om en stund."
      : serverDetail || `API-fel ${response.status}`;
    throw new ApiError(response.status,detail);
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

function initialCup(cups:Cup[]):Cup|undefined {
  const requested = Number(new URLSearchParams(window.location.search).get("cup"));
  const stored = Number(localStorage.getItem(CUP_KEY));
  return cups.find(cup => cup.id === requested)
    || cups.find(cup => cup.id === stored)
    || cups[0];
}

function rememberCup(cupId:number) {
  localStorage.setItem(CUP_KEY,String(cupId));
  const url = new URL(window.location.href);
  url.searchParams.set("cup",String(cupId));
  window.history.replaceState({},"",`${url.pathname}${url.search}${url.hash}`);
}

function forgetCup() {
  localStorage.removeItem(CUP_KEY);
  const url = new URL(window.location.href);
  url.searchParams.delete("cup");
  window.history.replaceState({},"",`${url.pathname}${url.search}${url.hash}`);
}

function currentAdminStep():AdminStep {
  const value=window.location.hash.replace(/^#/,"") as AdminStep;
  return nav.some(([,href])=>href===`#${value}`) ? value : "overview";
}

export default function AdminWorkspace({verifiedSession=null}:{verifiedSession?:(SessionPayload & {token:string})|null}) {
  const [token,setToken] = useState<string|null>(null);
  const [account,setAccount] = useState<Account|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [trashedCups,setTrashedCups] = useState<TrashedCup[]>([]);
  const [trashOpen,setTrashOpen] = useState(false);
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
  const [deletingCup,setDeletingCup] = useState(false);
  const [restoringSession,setRestoringSession] = useState(false);
  const [message,setMessage] = useState("");
  const [error,setError] = useState("");
  const [apiStatus,setApiStatus] = useState<ApiStatus>("checking");
  const [activeStep,setActiveStep] = useState<AdminStep>("overview");
  const [importWelcome,setImportWelcome] = useState<ImportWelcome|null>(null);
  const [kitBusy,setKitBusy] = useState(false);
  const [kitHint,setKitHint] = useState("");
  const [kitSuggestion,setKitSuggestion] = useState<KitSuggestion|null>(null);
  const [bulkKitBusy,setBulkKitBusy] = useState(false);
  const [bulkKitProgress,setBulkKitProgress] = useState("");

  const activeCup = useMemo(() => cups.find(cup => cup.id === cupId) || null,[cups,cupId]);
  const isOwnerAccount = account?.role === "owner" || account?.is_owner === true;

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null); setAccount(null); setCups([]); setTrashedCups([]); setTrashOpen(false); setCupId(null); setCupinfo(null); setTeams([]); setGroups([]);
    setPassword(""); setMessage(""); setError(""); setRestoringSession(false);
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

  const loadTrash = useCallback(async (nextToken:string) => {
    const data = await request<{cups:TrashedCup[]}>("/api/admin/trash",{},nextToken);
    setTrashedCups(data.cups || []);
  },[]);

  useEffect(() => {
    const sync=()=>setActiveStep(currentAdminStep());
    const onStep=(event:Event)=>setActiveStep((event as CustomEvent<AdminStep>).detail || "overview");
    sync();
    window.addEventListener("hashchange",sync);
    window.addEventListener("cupnavi:admin-step",onStep);
    return()=>{window.removeEventListener("hashchange",sync);window.removeEventListener("cupnavi:admin-step",onStep);};
  },[]);

  useEffect(()=>{
    if(!cupId)return;
    try{
      const raw=localStorage.getItem(IMPORT_WELCOME_KEY);
      const parsed=raw?JSON.parse(raw) as ImportWelcome:null;
      setImportWelcome(parsed?.cupId===cupId?parsed:null);
    }catch{localStorage.removeItem(IMPORT_WELCOME_KEY);setImportWelcome(null);}
  },[cupId]);

  function dismissImportWelcome(){localStorage.removeItem(IMPORT_WELCOME_KEY);if(cupId)localStorage.setItem(`${IMPORT_WELCOME_KEY}:dismissed:${cupId}`,"1");setImportWelcome(null);}

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(),8000);
    fetch(`${API_BASE}/health`,{cache:"no-store",signal:controller.signal})
      .then(response => { if (!response.ok) throw new Error("API unavailable"); setApiStatus("online"); })
      .catch(() => setApiStatus("offline"))
      .finally(() => window.clearTimeout(timeout));
    return () => { controller.abort(); window.clearTimeout(timeout); };
  },[]);

  useEffect(() => {
    let cancelled=false;
    let retryTimer:number|undefined;

    async function restoreSession() {
      if (verifiedSession) {
        const selected=initialCup(verifiedSession.cups || []);
        setToken(verifiedSession.token); setAccount(verifiedSession.account); setCups(verifiedSession.cups || []); setApiStatus("online");
        if(selected){setCupId(selected.id);rememberCup(selected.id);await loadCupInfo(verifiedSession.token,selected.id).catch(err=>{if(!cancelled)setError(err instanceof Error?`Cupens data kunde inte hämtas: ${err.message}`:"Cupens data kunde inte hämtas.");});}
        if(verifiedSession.account.role==="owner"||verifiedSession.account.is_owner===true)void loadTrash(verifiedSession.token).catch(()=>undefined);
        setRestoringSession(false);
        return;
      }
      const stored = localStorage.getItem(TOKEN_KEY);
      if (!stored || cancelled) { setRestoringSession(false); return; }
      setRestoringSession(true);
      try {
        const data = await request<SessionPayload>("/api/admin/session",{},stored);
        if (cancelled) return;
        setToken(stored); setAccount(data.account); setCups(data.cups || []); setApiStatus("online");
        const selected = initialCup(data.cups || []);
        if (selected) { setCupId(selected.id); rememberCup(selected.id); }
        setRestoringSession(false);

        if (data.account.role === "owner" || data.account.is_owner === true) {
          loadTrash(stored).catch(err => {
            if (!cancelled) setError(err instanceof Error ? `Papperskorgen kunde inte hämtas: ${err.message}` : "Papperskorgen kunde inte hämtas.");
          });
        }
        if (selected) {
          loadCupInfo(stored,selected.id).catch(err => {
            if (!cancelled) setError(err instanceof Error ? `Cupens data kunde inte hämtas: ${err.message}` : "Cupens data kunde inte hämtas.");
          });
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status===401) { logout(); return; }
        setApiStatus("offline");
        setError("Tillfälligt anslutningsproblem. Din inloggning ligger kvar och CupNavi försöker igen.");
        retryTimer=window.setTimeout(restoreSession,2200);
      }
    }

    void restoreSession();
    return()=>{ cancelled=true; if(retryTimer!==undefined) window.clearTimeout(retryTimer); };
  },[loadCupInfo,loadTrash,logout,verifiedSession]);

  async function login(event:FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    let data:SessionPayload;
    try {
      data = await request<SessionPayload>("/api/admin/session",{method:"POST",body:JSON.stringify({email,password})});
      if (!data.token) throw new Error("API:t returnerade ingen session.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inloggningen misslyckades.");
      setBusy(false);
      return;
    }

    localStorage.setItem(TOKEN_KEY,data.token!);
    setToken(data.token!); setAccount(data.account); setCups(data.cups || []); setPassword(""); setApiStatus("online");
    const selected = initialCup(data.cups || []);
    if (selected) { setCupId(selected.id); rememberCup(selected.id); }
    else setMessage("Kontot är giltigt men är inte kopplat till någon cup ännu.");
    setBusy(false);

    try {
      if (data.account.role === "owner" || data.account.is_owner === true) await loadTrash(data.token!);
      if (selected) await loadCupInfo(data.token!,selected.id);
    } catch (err) {
      setError(err instanceof Error ? `Du är inloggad, men all cupdata kunde inte hämtas: ${err.message}` : "Du är inloggad, men all cupdata kunde inte hämtas.");
    }
  }

  async function changeCup(nextId:number) {
    if (!token) return;
    if (!cups.some(cup => cup.id === nextId)) { setError("Cupen finns inte i din behöriga lista."); return; }
    setCupId(nextId); rememberCup(nextId); setBusy(true); setError(""); setMessage("");
    try { await loadCupInfo(token,nextId); }
    catch (err) { setError(err instanceof Error ? err.message : "Cupen kunde inte hämtas."); }
    finally { setBusy(false); }
  }

  async function removeCup() {
    if (!token || !activeCup || !isOwnerAccount || deletingCup) return;
    if (!window.confirm(`Flytta ${activeCup.name} till papperskorgen?\n\nCupen avpubliceras direkt men kan återställas från papperskorgen.`)) return;
    setDeletingCup(true); setError(""); setMessage("");
    const removedCup=activeCup;
    const previous={cups,cupId,cupinfo,teams,groups};
    const optimisticRemaining=cups.filter(cup=>cup.id!==removedCup.id);
    const optimisticNext=optimisticRemaining[0] || null;
    setCups(optimisticRemaining); setCupinfo(null); setTeams([]); setGroups([]);
    if(optimisticNext){setCupId(optimisticNext.id);rememberCup(optimisticNext.id);}
    else{setCupId(null);forgetCup();}
    setMessage(`${removedCup.name} flyttas till papperskorgen…`);
    try {
      const result = await request<DeleteCupPayload>(`/api/admin/cups/${removedCup.id}`,{
        method:"DELETE",body:JSON.stringify({confirmed_name:removedCup.name})
      },token);
      const remaining = result.cups || [];
      setCups(remaining);
      void loadTrash(token).catch(() => undefined);
      const nextCup = remaining.find(cup=>cup.id===optimisticNext?.id) || remaining[0];
      if (nextCup) {
        setCupId(nextCup.id); rememberCup(nextCup.id);
        void loadCupInfo(token,nextCup.id).catch(() => undefined);
        setMessage(`${removedCup.name} har flyttats till papperskorgen.`);
      } else {
        setCupId(null); forgetCup();
        setMessage(`${removedCup.name} har flyttats till papperskorgen. Det finns ingen aktiv cup kvar.`);
      }
    } catch (err) {
      setCups(previous.cups); setCupId(previous.cupId); setCupinfo(previous.cupinfo); setTeams(previous.teams); setGroups(previous.groups);
      if(previous.cupId)rememberCup(previous.cupId);else forgetCup();
      setMessage(""); setError(err instanceof Error ? `Cupen kunde inte tas bort och har återställts: ${err.message}` : "Cupen kunde inte tas bort och har återställts.");
    }
    finally { setDeletingCup(false); }
  }

  async function restoreCup(cup:TrashedCup) {
    if (!token || !isOwnerAccount) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await request<RestoreCupPayload>(`/api/admin/trash/${cup.id}/restore`,{method:"POST"},token);
      setCups(result.cups || []); setTrashedCups(result.trash || []);
      setCupId(result.cup.id); rememberCup(result.cup.id); await loadCupInfo(token,result.cup.id);
      setMessage(`${cup.name} har återställts som opublicerat utkast.`);
      if (!(result.trash || []).length) setTrashOpen(false);
    } catch (err) { setError(err instanceof Error ? err.message : "Cupen kunde inte återställas."); }
    finally { setBusy(false); }
  }

  async function emptyTrash() {
    if (!token || !isOwnerAccount || !trashedCups.length) return;
    if (!window.confirm(`Töm papperskorgen?\n\n${trashedCups.length} ${trashedCups.length === 1 ? "cup" : "cuper"} tas bort från papperskorgen och kan inte återställas i admin efter detta.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await request<{emptied:boolean;deleted:number;trash:TrashedCup[]}>("/api/admin/trash",{method:"DELETE"},token);
      const count = trashedCups.length;
      setTrashedCups([]); setTrashOpen(false);
      setMessage(`Papperskorgen är tömd. ${count} ${count === 1 ? "cup" : "cuper"} togs bort från återställningsvyn.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Papperskorgen kunde inte tömmas."); }
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
      setMessage("Cupinfo sparad.");
      window.location.hash="teams";
    } catch (err) { setError(err instanceof Error ? err.message : "Cupinfo kunde inte sparas."); }
    finally { setBusy(false); }
  }

  function beginTeamEdit(team:Team) {
    setEditingTeam(team.id);
    setTeamDraft({name:team.name,age_class:team.age_class || "",primary_color:team.primary_color || "#111827",secondary_color:team.secondary_color || "#FFFFFF",home_pattern:team.home_pattern||"Helfärgad",home_color_2:team.home_color_2||"#FFFFFF",away_pattern:team.away_pattern||"Helfärgad",away_color_2:team.away_color_2||"#111827",logo_url:team.logo_url||"",logo_source_url:team.logo_source_url||""});
    setKitSuggestion(null);setKitHint("");
    setError(""); setMessage("");
  }
  function cancelTeamEdit() { setEditingTeam(null); setTeamDraft(emptyTeam); setKitSuggestion(null); setKitHint(""); }

  async function searchKit(candidate?:KitCandidate) {
    if(!token||!cupId||!teamDraft.name.trim())return;
    setKitBusy(true);setError("");setMessage("");setKitSuggestion(null);
    try{
      const result=await request<KitSuggestion>(`/api/admin/cups/${cupId}/teams/kit-search`,{method:"POST",body:JSON.stringify({team_name:teamDraft.name,age_class:teamDraft.age_class||null,search_hint:kitHint||null,resolved_club:candidate?[candidate.name,candidate.location,candidate.country].filter(Boolean).join(" · "):null,resolved_source_url:candidate?.source_url||null})},token);
      setKitSuggestion(result);
    }catch(err){setError(err instanceof Error?err.message:"Tröjorna kunde inte sökas.");}
    finally{setKitBusy(false);}
  }

  function applyKitSuggestion(){
    if(!kitSuggestion)return;
    setTeamDraft(current=>({...current,
      ...(kitSuggestion.home_verified?{primary_color:kitSuggestion.home_color_1,home_color_2:kitSuggestion.home_color_2,home_pattern:kitSuggestion.home_pattern}:{}),
      ...(kitSuggestion.away_verified?{secondary_color:kitSuggestion.away_color_1,away_color_2:kitSuggestion.away_color_2,away_pattern:kitSuggestion.away_pattern}:{}),
      ...(kitSuggestion.logo_verified?{logo_url:kitSuggestion.logo_url,logo_source_url:kitSuggestion.logo_source_url}:{}),
    }));
    setMessage("Tröjförslaget är infört i formuläret. Spara laget för att bekräfta ändringen.");
  }

  async function searchAllTeamAssets(){
    if(!token||!cupId||!teams.length||bulkKitBusy)return;
    setBulkKitBusy(true);setError("");setMessage("");let completed=0,saved=0,failed=0;const updated:Team[]=[];
    for(let start=0;start<teams.length;start+=3){
      const batch=teams.slice(start,start+3);
      await Promise.all(batch.map(async team=>{try{
        const suggestion=await request<KitSuggestion>(`/api/admin/cups/${cupId}/teams/kit-search`,{method:"POST",body:JSON.stringify({team_name:team.name,age_class:team.age_class||null})},token);
        if(suggestion.identity_status==="ambiguous"||(!suggestion.home_verified&&!suggestion.away_verified&&!suggestion.logo_verified))return;
        const payload={...team,
          ...(suggestion.home_verified?{primary_color:suggestion.home_color_1,home_color_2:suggestion.home_color_2,home_pattern:suggestion.home_pattern}:{}),
          ...(suggestion.away_verified?{secondary_color:suggestion.away_color_1,away_color_2:suggestion.away_color_2,away_pattern:suggestion.away_pattern}:{}),
          ...(suggestion.logo_verified?{logo_url:suggestion.logo_url,logo_source_url:suggestion.logo_source_url}:{}),
        };
        const result=await request<Team>(`/api/admin/cups/${cupId}/teams/${team.id}`,{method:"PUT",body:JSON.stringify(payload)},token);updated.push(result);saved++;
      }catch{failed++;}finally{completed++;setBulkKitProgress(`${completed} av ${teams.length} lag kontrollerade`);}}));
    }
    setTeams(current=>current.map(team=>updated.find(item=>item.id===team.id)||team));
    setMessage(`${saved} lag uppdaterades med verifierade tröjor eller klubbmärken.${failed?` ${failed} sökningar misslyckades.`:""} Osäkra träffar lämnades oförändrade.`);
    setBulkKitBusy(false);
  }

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

  if (!account && restoringSession) {
    return <main className="admin-main admin-starting" aria-live="polite"><section className="admin-panel"><div className="admin-panel__top"><span>CUPNAVI</span><strong>ÅTERANSLUTER</strong></div><h2>Återställer din session</h2><p>Din inloggning ligger kvar. CupNavi väntar på ett stabilt svar från servern.</p></section></main>;
  }

  if (!account) {
    return <main className="admin-main" style={{maxWidth:720,margin:"0 auto"}}>
      <header className="admin-pagehead"><div><p className="kicker">ADMIN</p><h1>Logga in</h1><p>Logga in för att administrera dina cuper.</p></div></header>
      <form className="admin-panel admin-cupinfo" onSubmit={login}>
        <div className="admin-panel__top"><span>INLOGGNING</span><strong className={`admin-api-status is-${apiStatus}`}>{apiStatus==="online"?"SERVER ONLINE":apiStatus==="offline"?"ÅTERANSLUTER":"KONTROLLERAR"}</strong></div>
        <h2>Cupadministration</h2>
        <div className="admin-form-grid">
          <label>E-post<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required /></label>
          <label>Lösenord<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label>
        </div>
        <div className="admin-form-footer"><span role={error?"alert":undefined}>{error || (apiStatus==="offline" ? "Servern vaknar eller anslutningen är tillfälligt bruten." : "")}</span><button type="submit" disabled={busy||apiStatus==="offline"}>{busy?"Loggar in…":"Logga in"}</button></div>
        <details className="admin-login-help"><summary>Glömt lösenordet?</summary><p>En behörig ägare behöver ange ett nytt lösenord. CupNavi visar aldrig befintliga lösenord.</p></details>
      </form>
    </main>;
  }

  const publicCup = activeCup?.public_slug ? `/cup/${activeCup.public_slug}` : null;
  const isOwner = account.role === "owner" || account.is_owner === true;
  const groupedTeams = teams.filter(team=>team.group_id != null).length;
  const cupinfoReady=Boolean(cupinfo?.name&&cupinfo?.start_date);
  const teamsReady=teams.length>0;
  const groupsReady=teamsReady&&groups.length>0&&groupedTeams===teams.length;
  const nextTask=!cupinfoReady
    ? {href:"#cupinfo",label:"Komplettera Cupinfo",detail:"Kontrollera cupnamn och datum."}
    : !teamsReady
      ? {href:"#teams",label:"Lägg till lagen",detail:"Registrera lagen och deras matchställ."}
      : !groupsReady
        ? {href:"#groups",label:"Gör gruppindelningen",detail:`${teams.length-groupedTeams} lag saknar fortfarande grupp.`}
        : {href:"#venues",label:"Kontrollera planer och tider",detail:"Ange cupens kapacitet innan schemat skapas."};
  const checks=[
    {name:"Cupinfo",status:cupinfoReady?"Klar":"Komplettera",href:"#cupinfo",state:cupinfoReady?"done":"next"},
    {name:"Lag",status:teamsReady?`${teams.length} registrerade`:"Saknas",href:"#teams",state:teamsReady?"done":cupinfoReady?"next":"todo"},
    {name:"Grupper",status:groups.length?`${groupedTeams}/${teams.length} lag placerade`:"Saknas",href:"#groups",state:groupsReady?"done":teamsReady?"next":"todo"},
    {name:"Planer & tider",status:groupsReady?"Redo att kontrollera":"Väntar",href:"#venues",state:groupsReady?"next":"todo"},
    {name:"Publicering",status:activeCup?.is_published?"Publicerad":"Senare",href:"#publish",state:activeCup?.is_published?"done":"todo"},
  ];

  return <main className="admin-workspace">
    <aside className="admin-sidebar">
      <div className="admin-sidebar__cup"><span>AKTIV CUP</span><strong>{activeCup?.name || "Ingen cup"}</strong><small>{activeCup?.start_date || "Datum saknas"}</small></div>
      {cups.length > 1 && <label className="admin-cup-switcher"><span>Byt cup</span><select value={cupId || ""} onChange={e=>changeCup(Number(e.target.value))}>{cups.map(cup=><option key={cup.id} value={cup.id}>{cup.name}</option>)}</select></label>}
      {isOwner && <>
        <div className="admin-owner-actions">
          {activeCup && <button className="admin-remove-cup" type="button" disabled={deletingCup} onClick={()=>void removeCup()}>{deletingCup?"Tar bort…":"Ta bort cup"}</button>}
          <button className={`admin-trash-button${trashOpen?" is-open":""}`} type="button" onClick={()=>setTrashOpen(value=>!value)}>Papperskorg <span>{trashedCups.length}</span></button>
        </div>
        {trashOpen && <section className="admin-trash-panel" aria-label="Papperskorg">
          <div className="admin-trash-head"><strong>Papperskorg</strong><span>{trashedCups.length} {trashedCups.length===1?"cup":"cuper"}</span></div>
          {trashedCups.length ? <>
            <div className="admin-trash-list">{trashedCups.map(cup=><div key={cup.id}><span><strong>{cup.name}</strong><small>{cup.start_date || "Datum saknas"}</small></span><button type="button" disabled={busy} onClick={()=>void restoreCup(cup)}>Återställ</button></div>)}</div>
            <button className="admin-empty-trash" type="button" disabled={busy} onClick={()=>void emptyTrash()}>Töm papperskorg</button>
          </> : <p className="admin-trash-empty">Papperskorgen är tom.</p>}
        </section>}
      </>}
      <nav aria-label="Cupadministration">{nav.map(([item,href],index)=><Fragment key={item}>{adminPhaseStarts[index]&&<strong className="admin-nav-phase">{adminPhaseStarts[index]}</strong>}<a className={href===`#${activeStep}`?"is-active":""} href={href}><span>{String(index+1).padStart(2,"0")}</span>{item}</a></Fragment>)}</nav>
      {publicCup && <a className="admin-public-link" href={publicCup}>Visa publik cup ↗</a>}
      <button className="admin-public-link" type="button" onClick={logout}>Logga ut</button>
    </aside>

    <section className="admin-main" id="overview">
      <header className="admin-pagehead"><div><h1>Cupöversikt</h1></div><div className="admin-pagehead__actions"><span className="admin-draft">{activeCup?.is_published?"PUBLICERAD":"UTKAST"}</span>{publicCup&&<a href={publicCup}>Förhandsgranska</a>}</div></header>
      {activeStep==="overview"&&importWelcome&&<section className="admin-import-welcome" aria-labelledby="import-welcome-title">
        <div className="admin-import-welcome__top"><span>IMPORTEN ÄR KLAR</span><button type="button" onClick={dismissImportWelcome} aria-label="Dölj introduktionen">×</button></div>
        <div className="admin-import-welcome__hero"><div className="admin-import-welcome__check">✓</div><div><h2 id="import-welcome-title">{importWelcome.cupName} är skapad</h2><p>CupNavi har lagt in underlaget. Kontrollera uppgifterna innan du publicerar.</p></div></div>
        <div className="admin-import-welcome__facts"><span><b>{importWelcome.teams}</b> lag</span><span><b>{importWelcome.groups}</b> grupper</span><span><b>{importWelcome.matches}</b> matcher</span><span><b>{importWelcome.venues}</b> planer</span></div>
        <ol className="admin-import-welcome__steps"><li><b>Kontrollera cupinfo</b><span>Namn, datum, arrangör och adress.</span></li><li><b>Kontrollera planer och schema</b><span>Säkerställ tider, planer och vilopauser.</span></li><li><b>Förhandsgranska och publicera</b><span>Se publikvyn och publicera när allt stämmer.</span></li></ol>
        <div className="admin-import-welcome__actions"><a className="is-primary" href="#cupinfo">Börja med Cupinfo →</a><a href="#schedule">Kontrollera schemat</a></div>
      </section>}
      {activeStep==="overview"&&!activeCup?.is_published&&<a className="admin-next-task" href={nextTask.href}><span>NÄSTA UPPGIFT</span><strong>{nextTask.label} →</strong><small>{nextTask.detail}</small></a>}
      {(error||message) && <section className="admin-panel" style={{marginBottom:14}}><strong>{error?"Meddelande":"Klart"}</strong><p>{error||message}</p></section>}
      <section className="admin-dashboard-grid">
        <article className="admin-panel admin-panel--status"><div className="admin-panel__top"><span>STATUS</span><strong>{activeCup?.is_published?"LIVE":"ARBETE PÅGÅR"}</strong></div><h2>{activeCup?.is_published?"Cupen är publicerad":"Vägen till publicering"}</h2><div className="admin-checks">{checks.map(check=><a href={check.href} className={`is-${check.state}`} key={check.name}><span>{check.state==="done"?"✓":check.state==="next"?"→":"○"}</span><strong>{check.name}</strong><small>{check.status}</small></a>)}</div></article>
        <article className="admin-panel admin-panel--codes"><div className="admin-panel__top"><span>KONTO</span><strong>VERIFIERAT</strong></div><h2>Åtkomst</h2><p>{isOwner ? "Ägarkonto med åtkomst till alla cuper." : "Arrangörskonto med åtkomst till tilldelade cuper."}</p><div className="admin-code-placeholder">Konto <b>{account.email}</b></div><div className="admin-code-placeholder">Roll <b>{isOwner ? "ägare" : activeCup?.role || "—"}</b></div></article>
      </section>

      {activeStep==="cupinfo" && <form className="admin-panel admin-cupinfo" id="cupinfo" onSubmit={saveCupInfo}>
        <div className="admin-panel__top"><span>02 / CUPINFO</span><strong>{busy?"ARBETAR":"REDO"}</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Grunduppgifter</h2><p>Uppgifterna för den valda cupen.</p></div><span className="admin-lock">BEHÖRIG</span></div>
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
          <div className="admin-form-footer"><span>{message || ""}</span><button type="submit" disabled={busy || !cupinfo.name.trim()}>{busy?"Sparar…":"Spara och fortsätt till Lag →"}</button></div>
        </> : <p>{busy?"Hämtar Cupinfo…":"Cupinfo kunde inte hämtas ännu."}</p>}
      </form>}

      {activeStep==="teams" && <section className="admin-panel admin-teams" id="teams">
        <div className="admin-panel__top"><span>03 / LAG</span><strong>{teams.length} REGISTRERADE</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Lag</h2><p>Skapa och redigera lag.</p></div><span className="admin-lock">REDIGERING</span></div>
        {teams.length>0&&<div className="admin-bulk-assets"><div><strong>Tröjor och klubbmärken</strong><span>{bulkKitProgress||"Sök igenom alla lag och spara bara entydigt verifierade träffar."}</span></div><button type="button" disabled={bulkKitBusy} onClick={()=>void searchAllTeamAssets()}>{bulkKitBusy?"Söker…":"Sök för alla lag"}</button></div>}
        <form onSubmit={saveTeam} className="admin-team-editor">
          <div className="admin-form-grid">
            <label>Lagnamn<input value={teamDraft.name} onChange={e=>setTeamDraft({...teamDraft,name:e.target.value})} required placeholder="Exempel: ÖSK P2014 Svart" /></label>
            <label>Klass<input value={teamDraft.age_class} onChange={e=>setTeamDraft({...teamDraft,age_class:e.target.value})} placeholder="Exempel: P2014" /></label>
            <section className="admin-kit-editor">
              <div className="admin-kit-editor__head"><span className="admin-kit-editor__shirt" style={{background:kitBackground(teamDraft.home_pattern,teamDraft.primary_color,teamDraft.home_color_2)}} aria-hidden="true"/><div><h3>Hemmaställ</h3><p>Välj mönster och tröjfärger.</p></div></div>
              <label>Mönster<select value={teamDraft.home_pattern} onChange={e=>setTeamDraft({...teamDraft,home_pattern:e.target.value as KitPattern})}>{kitPatterns.map(pattern=><option key={pattern}>{pattern}</option>)}</select></label>
              <span className="admin-kit-color-label">Huvudfärg</span><StandardKitColor label="Hemmaställets huvudfärg" value={teamDraft.primary_color} onChange={primary_color=>setTeamDraft({...teamDraft,primary_color})}/>
              {teamDraft.home_pattern!=="Helfärgad"&&<><span className="admin-kit-color-label">Andra färg</span><StandardKitColor label="Hemmaställets andra färg" value={teamDraft.home_color_2} onChange={home_color_2=>setTeamDraft({...teamDraft,home_color_2})}/></>}
            </section>
            <section className="admin-kit-editor">
              <div className="admin-kit-editor__head"><span className="admin-kit-editor__shirt" style={{background:kitBackground(teamDraft.away_pattern,teamDraft.secondary_color,teamDraft.away_color_2)}} aria-hidden="true"/><div><h3>Bortaställ</h3><p>Välj ett tydligt alternativ till hemmastället.</p></div></div>
              <label>Mönster<select value={teamDraft.away_pattern} onChange={e=>setTeamDraft({...teamDraft,away_pattern:e.target.value as KitPattern})}>{kitPatterns.map(pattern=><option key={pattern}>{pattern}</option>)}</select></label>
              <span className="admin-kit-color-label">Huvudfärg</span><StandardKitColor label="Bortaställets huvudfärg" value={teamDraft.secondary_color} onChange={secondary_color=>setTeamDraft({...teamDraft,secondary_color})}/>
              {teamDraft.away_pattern!=="Helfärgad"&&<><span className="admin-kit-color-label">Andra färg</span><StandardKitColor label="Bortaställets andra färg" value={teamDraft.away_color_2} onChange={away_color_2=>setTeamDraft({...teamDraft,away_color_2})}/></>}
            </section>
            <div className="admin-logo-editor">
              {teamDraft.logo_url?<img src={teamDraft.logo_url} alt="Förhandsvisning av klubbmärke" referrerPolicy="no-referrer"/>:<span aria-hidden="true">CN</span>}
              <label>Klubbmärke<small>Klistra in en bildadress eller använd sökningen nedan.</small><input type="url" value={teamDraft.logo_url} onChange={e=>setTeamDraft({...teamDraft,logo_url:e.target.value})} placeholder="https://klubb.se/logo.png" /></label>
            </div>
          </div>
          <section className="admin-kit-search" aria-label="Sök lagets matchställ">
            <div><strong>Sök tröjfärger och mönster</strong><span>CupNavi söker på nätet och visar källorna. Du bestämmer vad som sparas.</span></div>
            <label>Sökledtråd <input value={kitHint} onChange={e=>setKitHint(e.target.value)} placeholder="Valfritt: klubbens ort eller webbplats" /></label>
            <button type="button" disabled={kitBusy||!teamDraft.name.trim()} onClick={()=>void searchKit()}>{kitBusy?"Söker på nätet…":"Sök matchställ"}</button>
          </section>
          {kitSuggestion&&<section className="admin-kit-result">
            {kitSuggestion.candidate_matches?.length>0&&!kitSuggestion.found?<><strong>Vilken klubb är rätt?</strong><p>Flera möjliga klubbar hittades. Välj rätt identitet innan färger används.</p><div className="admin-kit-candidates">{kitSuggestion.candidate_matches.map(candidate=><button type="button" key={candidate.source_url} onClick={()=>void searchKit(candidate)}><b>{candidate.name}</b><span>{[candidate.location,candidate.country].filter(Boolean).join(" · ")}</span><small>{candidate.reason}</small></button>)}</div></>:<><div className="admin-kit-result__head"><div><span>{kitSuggestion.confidence==="high"?"HÖG SÄKERHET":kitSuggestion.confidence==="medium"?"MEDEL SÄKERHET":"LÅG SÄKERHET"}</span><strong>{kitSuggestion.club_match||teamDraft.name}</strong></div><button type="button" disabled={!kitSuggestion.home_verified&&!kitSuggestion.away_verified&&!kitSuggestion.logo_verified} onClick={applyKitSuggestion}>Använd verifierade uppgifter</button></div><div className="admin-kit-options"><div><i className="admin-kit-swatch" style={{background:kitBackground(kitSuggestion.home_pattern,kitSuggestion.home_color_1,kitSuggestion.home_color_2)} as CSSProperties}/><span><b>Hemma · {kitSuggestion.home_pattern}</b><small>{kitSuggestion.home_verified?kitSuggestion.home_evidence:"Inte verifierat"}</small></span></div><div><i className="admin-kit-swatch" style={{background:kitBackground(kitSuggestion.away_pattern,kitSuggestion.away_color_1,kitSuggestion.away_color_2)} as CSSProperties}/><span><b>Borta · {kitSuggestion.away_pattern}</b><small>{kitSuggestion.away_verified?kitSuggestion.away_evidence:"Inte verifierat"}</small></span></div>{kitSuggestion.logo_verified&&<div><img className="admin-kit-logo-result" src={kitSuggestion.logo_url} alt="Hittat klubbmärke" referrerPolicy="no-referrer"/><span><b>Klubbmärke</b><small>Verifierat mot klubbkällan</small></span></div>}</div><details><summary>Visa källor</summary><ul>{[...new Set([...(kitSuggestion.home_sources||[]),...(kitSuggestion.away_sources||[]),...(kitSuggestion.logo_source_url?[kitSuggestion.logo_source_url]:[])])].map(url=><li key={url}><a href={url} target="_blank" rel="noreferrer">{url}</a></li>)}</ul></details></>}
          </section>}
          <div className="admin-form-footer"><span>{editingTeam?"Du redigerar ett befintligt lag.":""}</span><div className="admin-team-actions">{editingTeam&&<button type="button" onClick={cancelTeamEdit}>Avbryt</button>}<button type="submit" disabled={busy||!teamDraft.name.trim()}>{busy?"Sparar…":editingTeam?"Spara lag":"Lägg till lag"}</button></div></div>
        </form>
        <div className="admin-team-list admin-team-roster">
          {teams.length ? teams.map(team=><article key={team.id} className={editingTeam===team.id?"is-editing":""}>
            {team.logo_url?<img className="admin-team-logo" src={team.logo_url} alt={`${team.name} klubbmärke`} loading="lazy" referrerPolicy="no-referrer"/>:<span className="admin-team-logo is-empty" aria-hidden="true">CN</span>}
            <span className="admin-team-kits" aria-label="Hemma- och bortaställ"><span className="admin-team-shirt" title="Hemmaställ" style={{background:kitBackground(team.home_pattern||"Helfärgad",team.primary_color||"#111827",team.home_color_2||"#FFFFFF")}}/><span className="admin-team-shirt" title="Bortaställ" style={{background:kitBackground(team.away_pattern||"Helfärgad",team.secondary_color||"#FFFFFF",team.away_color_2||"#111827")}}/></span>
            <div><strong>{team.name}</strong><small>{team.age_class||"Klass saknas"}{team.group_id?` · ${groups.find(group=>group.id===team.group_id)?.name || `Grupp ${team.group_id}`}`:" · Ej gruppindelat"}</small></div>
            <div className="admin-team-actions"><button type="button" onClick={()=>beginTeamEdit(team)}>Redigera</button><button className="is-danger" type="button" onClick={()=>removeTeam(team)}>Ta bort</button></div>
          </article>) : <div className="admin-empty"><strong>Inga lag ännu</strong><span>Lägg till det första laget ovan.</span></div>}
        </div>
        {teams.length>0&&<div className="admin-step-complete"><span>Alla lag inlagda och kontrollerade?</span><a href="#groups">Klar med lag → Grupper</a></div>}
      </section>}

      {activeStep==="groups" && <section className="admin-panel admin-teams" id="groups">
        <div className="admin-panel__top"><span>04 / GRUPPER</span><strong>{groups.length} GRUPPER · {groupedTeams}/{teams.length} LAG</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Gruppindelning</h2><p>Skapa grupper och placera lagen.</p></div><span className="admin-lock">REDIGERING</span></div>
        <form onSubmit={saveGroup} className="admin-team-editor">
          <div className="admin-form-grid">
            <label>Gruppnamn<input value={groupDraft.name} onChange={e=>setGroupDraft({...groupDraft,name:e.target.value})} required placeholder="Exempel: Grupp A" /></label>
            <label>Klass<input value={groupDraft.age_class} onChange={e=>setGroupDraft({...groupDraft,age_class:e.target.value})} placeholder="Exempel: P2014" /></label>
          </div>
          <div className="admin-form-footer"><span>{editingGroup?"Du redigerar en befintlig grupp.":""}</span><div className="admin-team-actions">{editingGroup&&<button type="button" onClick={cancelGroupEdit}>Avbryt</button>}<button type="submit" disabled={busy||!groupDraft.name.trim()}>{busy?"Sparar…":editingGroup?"Spara grupp":"Skapa grupp"}</button></div></div>
        </form>
        <div className="admin-team-list admin-group-list">
          {groups.length ? groups.map(group=><article key={group.id} className={editingGroup===group.id?"is-editing":""}>
            <div><strong>{group.name}</strong><small>{group.age_class||"Ingen klass"} · {group.team_count} lag</small></div>
            <div className="admin-team-actions"><button type="button" onClick={()=>beginGroupEdit(group)}>Redigera</button><button className="is-danger" type="button" onClick={()=>removeGroup(group)} disabled={group.team_count>0}>Ta bort</button></div>
          </article>) : <div className="admin-empty"><strong>Inga grupper ännu</strong><span>Skapa den första gruppen ovan.</span></div>}
        </div>
        <div className="admin-team-list admin-group-assignments" style={{marginTop:18}}>
          {teams.map(team=><article key={`group-team-${team.id}`}>
            <div><strong>{team.name}</strong><small>{team.age_class||"Klass saknas"}</small></div>
            <label style={{marginLeft:"auto"}}>Grupp<select value={team.group_id ?? ""} disabled={busy} onChange={e=>assignGroup(team,e.target.value?Number(e.target.value):null)}><option value="">Ej gruppindelat</option>{groups.map(group=><option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
          </article>)}
        </div>
        {teams.length>0&&groupedTeams===teams.length&&<div className="admin-step-complete"><span>Alla lag är gruppindelade.</span><a href="#venues">Fortsätt till Planer & tider →</a></div>}
      </section>}

      {activeStep==="venues" && token && cupId && <VenueAdmin token={token} cupId={cupId} />}
      {activeStep==="rules" && token && cupId && <RulesAdmin token={token} cupId={cupId} />}
      {activeStep==="schedule" && token && cupId && <ScheduleAdmin token={token} cupId={cupId} />}
      {activeStep==="referees" && token && cupId && <RefereeAdmin token={token} cupId={cupId} />}
      {activeStep==="playoffs" && token && cupId && <PlayoffAdmin token={token} cupId={cupId} />}

      {activeStep==="export" && token && cupId && <ExportAdmin token={token} cupId={cupId}/>}
    </section>
  </main>;
}
