"use client";

import { CSSProperties, FormEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import VenueAdmin from "./venue-admin";
import RulesAdmin from "./rules-admin";
import ScheduleAdmin from "./schedule-admin";
import RefereeAdmin from "./referee-admin";
import PlayoffAdmin from "./playoff-admin";
import ExportAdmin from "./export-admin";
import { TeamKit } from "./TeamKit";
import { CLIENT_API_BASE } from "../lib/client-api";
import AccessAdmin from "./access-admin";

const API_BASE = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";
const IMPORT_WELCOME_KEY = "cupnavi_import_welcome_v1";

const setupNav = [
  ["Översikt", "#overview"], ["Cupinfo", "#cupinfo"], ["Lag", "#teams"], ["Grupper", "#groups"],
  ["Planer & tider", "#venues"], ["Regler", "#rules"], ["Schema", "#schedule"],
  ["Slutspel", "#playoffs"], ["Kontroll & publicering", "#publish"]
];
const toolNav = [["Användare", "#access"], ["Domare", "#referees"], ["Matchrapportering", "#reporting"], ["Uppdatera från fil", "#import"], ["PDF & export", "#export"]];
const nav=[...setupNav,...toolNav];

type Account = { id:number; email:string; display_name?:string|null; role?:string|null; is_owner?:boolean };
type Cup = { id:number; name:string; public_slug?:string|null; start_date?:string|null; end_date?:string|null; created_at?:string|null; is_published?:number|boolean; role:string };
type TrashedCup = Cup & { trashed_at?:string|null };
type CupInfo = {
  id:number; public_slug?:string|null; is_published?:number|boolean;
  name:string; start_date?:string|null; end_date?:string|null; organizer?:string|null;
  arena_address?:string|null; organizer_phone?:string|null; feedback_email?:string|null;
  public_information?:string|null;
  arrangement_type?:"matchcamp"|"tournament"|"tournament_playoffs"|"custom"|null;
  admin_revision:number;
};
type SessionPayload = { account:Account; cups:Cup[]; token?:string };
type AdminStep = "overview"|"cupinfo"|"teams"|"groups"|"venues"|"rules"|"schedule"|"referees"|"playoffs"|"publish"|"reporting"|"import"|"export"|"access";
type DeleteCupPayload = { deleted:boolean; recoverable:boolean; cup:Cup; cups:Cup[] };
type RestoreCupPayload = { restored:boolean; cup:Cup; cups:Cup[]; trash:TrashedCup[] };
type ApiStatus = "checking" | "online" | "offline";
const comparableCupName=(value:string)=>value.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-zA-Z0-9]/g,"").toLocaleLowerCase("sv");
const createdLabel=(value?:string|null)=>{if(!value)return "skapad tid saknas";const normalized=/[zZ]|[+-]\d\d:?\d\d$/.test(value)?value:`${value.replace(" ","T")}Z`;const date=new Date(normalized);return Number.isNaN(date.getTime())?"skapad tid saknas":`skapad ${new Intl.DateTimeFormat("sv-SE",{dateStyle:"medium",timeStyle:"short"}).format(date)}`;};
type KitPattern = "Helfärgad"|"Vertikala ränder"|"Horisontella ränder"|"Rutigt"|"Delad"|"Diagonala ränder"|"Grafiskt";
type Team = { id:number; tournament_id:number; name:string; group_id?:number|null; age_class?:string|null; primary_color?:string|null; secondary_color?:string|null; home_pattern?:KitPattern|null; home_color_2?:string|null; away_pattern?:KitPattern|null; away_color_2?:string|null; logo_url?:string|null; logo_source_url?:string|null };
type Group = { id:number; tournament_id:number; name:string; age_class?:string|null; team_count:number };
type ScheduleOverview = {
  match_count:number; scheduled_count:number; unscheduled_count:number; pitch_count:number;
  schedule_dirty:boolean; conflict_analysis:{error_count:number;warning_count:number};
};
type ImportWelcome = { cupId:number; cupName:string; teams:number; groups:number; matches:number; venues:number; playoffs?:number };
type KitCandidate = {name:string;location:string;country:string;source_url:string;reason:string;confidence:string};
type KitSuggestion = {found:boolean;confidence:"low"|"medium"|"high";reason:string;club_match:string;identity_status:string;home_verified:boolean;away_verified:boolean;home_pattern:KitPattern;home_color_1:string;home_color_2:string;away_pattern:KitPattern;away_color_1:string;away_color_2:string;home_evidence:string;away_evidence:string;home_sources:string[];away_sources:string[];candidate_matches:KitCandidate[];logo_url:string;logo_source_url:string;logo_verified:boolean};
const emptyTeam = {name:"",age_class:"",primary_color:"#111827",secondary_color:"#FFFFFF",home_pattern:"Helfärgad" as KitPattern,home_color_2:"#FFFFFF",away_pattern:"Helfärgad" as KitPattern,away_color_2:"#111827",logo_url:"",logo_source_url:""};
const emptyGroup = {name:"",age_class:""};
const kitPatterns:KitPattern[]=["Helfärgad","Vertikala ränder","Horisontella ränder","Rutigt","Delad","Diagonala ränder","Grafiskt"];
const standardKitColors=[
  {name:"Vit",value:"#FFFFFF"},{name:"Svart",value:"#111827"},{name:"Röd",value:"#D72638"},
  {name:"Mörkblå",value:"#12355B"},{name:"Blå",value:"#246BCE"},{name:"Ljusblå",value:"#68B7E8"},
  {name:"Grön",value:"#238636"},{name:"Gul",value:"#F4C430"},{name:"Orange",value:"#F28C28"},
  {name:"Lila",value:"#713E8A"},{name:"Rosa",value:"#E56B9F"},{name:"Grå",value:"#7A8588"},
];
function normalizedWebUrl(value:string){const text=value.trim();return text&&/^www\./i.test(text)?`https://${text}`:text;}
function kitBackground(pattern:KitPattern,c1:string,c2:string){
  if(pattern==="Vertikala ränder")return `repeating-linear-gradient(90deg,${c1} 0 8px,${c2} 8px 16px)`;
  if(pattern==="Horisontella ränder")return `repeating-linear-gradient(0deg,${c1} 0 8px,${c2} 8px 16px)`;
  if(pattern==="Rutigt")return `conic-gradient(${c1} 25%,${c2} 0 50%,${c1} 0 75%,${c2} 0) 0 0/16px 16px`;
  if(pattern==="Delad")return `linear-gradient(90deg,${c1} 0 50%,${c2} 50%)`;
  if(pattern==="Diagonala ränder")return `repeating-linear-gradient(135deg,${c1} 0 8px,${c2} 8px 16px)`;
  if(pattern==="Grafiskt")return `linear-gradient(135deg,${c1} 0 42%,${c2} 42% 58%,${c1} 58%)`;
  return c1;
}
function StandardKitColor({value,onChange,label}:{value:string;onChange:(value:string)=>void;label:string}){
  return <div className="admin-kit-palette" role="group" aria-label={label}>{standardKitColors.map(color=><button key={color.value} type="button" className={value.toUpperCase()===color.value?"is-selected":""} style={{"--choice-color":color.value} as CSSProperties} title={color.name} aria-label={color.name} aria-pressed={value.toUpperCase()===color.value} onClick={()=>onChange(color.value)}><span aria-hidden="true"/></button>)}</div>;
}
function TeamLogo({team}:{team:Team}){
  const [failed,setFailed]=useState(false);
  const showImage=Boolean(team.logo_url)&&!failed;
  return <span className={`admin-team-logo${showImage?"":" is-empty"}`} aria-label={showImage?`${team.name} klubbmärke`:`${team.name} saknar klubbmärke`}>
    {showImage?<img src={normalizedWebUrl(team.logo_url||"")} alt="" loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>:<b>{team.name.slice(0,2).toLocaleUpperCase("sv")}</b>}
  </span>;
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
    arrangement_type:value.arrangement_type || "tournament",
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

export default function AdminWorkspace({verifiedSession=null,children=null}:{verifiedSession?:(SessionPayload & {token:string})|null;children?:ReactNode}) {
  const [token,setToken] = useState<string|null>(null);
  const [account,setAccount] = useState<Account|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [trashedCups,setTrashedCups] = useState<TrashedCup[]>([]);
  const [trashOpen,setTrashOpen] = useState(false);
  const [cupId,setCupId] = useState<number|null>(null);
  const [cupinfo,setCupinfo] = useState<CupInfo|null>(null);
  const [teams,setTeams] = useState<Team[]>([]);
  const [groups,setGroups] = useState<Group[]>([]);
  const [scheduleOverview,setScheduleOverview] = useState<ScheduleOverview|null>(null);
  const [teamDraft,setTeamDraft] = useState(emptyTeam);
  const [groupDraft,setGroupDraft] = useState(emptyGroup);
  const [editingTeam,setEditingTeam] = useState<number|null>(null);
  const [teamFormOpen,setTeamFormOpen] = useState(false);
  const teamFormRef = useRef<HTMLFormElement|null>(null);
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
  const [assetFocus,setAssetFocus] = useState<"kit"|"logo">("kit");
  const [bulkKitBusy,setBulkKitBusy] = useState(false);
  const [bulkKitProgress,setBulkKitProgress] = useState("");
  const [bulkKitResult,setBulkKitResult] = useState("");
  const [bulkKitIssues,setBulkKitIssues] = useState<Array<{teamId:number;teamName:string;reason:string}>>([]);

  const activeCup = useMemo(() => cups.find(cup => cup.id === cupId) || null,[cups,cupId]);
  const publishedTwin = useMemo(() => {
    if(!activeCup||activeCup.is_published)return null;
    const key=comparableCupName(activeCup.name);
    return cups.find(cup=>cup.id!==activeCup.id&&Boolean(cup.is_published)&&comparableCupName(cup.name)===key)||null;
  },[activeCup,cups]);
  const isOwnerAccount = account?.role === "owner" || account?.is_owner === true || activeCup?.role === "owner";

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null); setAccount(null); setCups([]); setTrashedCups([]); setTrashOpen(false); setCupId(null); setCupinfo(null); setTeams([]); setGroups([]);
    setPassword(""); setMessage(""); setError(""); setRestoringSession(false);
  },[]);

  const loadCupInfo = useCallback(async (nextToken:string, nextCupId:number) => {
    const [data,teamData,groupData,scheduleData] = await Promise.all([
      request<CupInfo>(`/api/admin/cups/${nextCupId}/cupinfo`,{},nextToken),
      request<{teams:Team[]}>(`/api/admin/cups/${nextCupId}/teams`,{},nextToken),
      request<{groups:Group[]}>(`/api/admin/cups/${nextCupId}/groups`,{},nextToken),
      request<ScheduleOverview>(`/api/admin/cups/${nextCupId}/schedule`,{},nextToken),
    ]);
    const normalized=cleanCupInfo(data); setCupinfo(normalized); setTeams(teamData.teams || []); setGroups(groupData.groups || []); setScheduleOverview(scheduleData);
    document.documentElement.dataset.arrangementType=normalized.arrangement_type || "tournament";
    window.dispatchEvent(new CustomEvent("cupnavi:arrangement-type",{detail:normalized.arrangement_type || "tournament"}));
    setEditingTeam(null); setTeamFormOpen(false); setTeamDraft(emptyTeam); setEditingGroup(null); setGroupDraft(emptyGroup);
  },[]);

  const refreshScheduleOverview = useCallback(async () => {
    if(!token||!cupId)return;
    try{setScheduleOverview(await request<ScheduleOverview>(`/api/admin/cups/${cupId}/schedule`,{},token));}
    catch{/* Schedule page owns detailed error handling; keep the last known overview here. */}
  },[token,cupId]);

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

  useEffect(()=>{if(activeStep==="overview")void refreshScheduleOverview();},[activeStep,refreshScheduleOverview]);

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
        void loadTrash(verifiedSession.token).catch(()=>undefined);
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

        loadTrash(stored).catch(err => {
          if (!cancelled) setError(err instanceof Error ? `Papperskorgen kunde inte hämtas: ${err.message}` : "Papperskorgen kunde inte hämtas.");
        });
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
      await loadTrash(data.token!);
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
    if (!token) return;
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
    if (!token || !trashedCups.length) return;
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
        body:JSON.stringify({name:cupinfo.name,start_date:cupinfo.start_date || null,end_date:cupinfo.end_date || null,organizer:cupinfo.organizer || null,arena_address:cupinfo.arena_address || null,organizer_phone:cupinfo.organizer_phone || null,feedback_email:cupinfo.feedback_email || null,public_information:cupinfo.public_information || null,arrangement_type:cupinfo.arrangement_type || "tournament",expected_revision:cupinfo.admin_revision})
      },token);
      const normalized = cleanCupInfo(saved);
      setCupinfo(normalized);
      document.documentElement.dataset.arrangementType=normalized.arrangement_type || "tournament";
      window.dispatchEvent(new CustomEvent("cupnavi:arrangement-type",{detail:normalized.arrangement_type || "tournament"}));
      setCups(current => current.map(cup => cup.id === cupId ? {...cup,name:normalized.name,start_date:normalized.start_date,end_date:normalized.end_date,public_slug:normalized.public_slug,is_published:normalized.is_published} : cup));
      setMessage("Cupinfo sparad.");
      window.location.hash="teams";
    } catch (err) {
      if(err instanceof ApiError&&err.status===409){await loadCupInfo(token,cupId).catch(()=>undefined);setError("En annan administratör hann ändra Cupinfo. Den senaste versionen har hämtats; kontrollera uppgifterna innan du sparar igen.");}
      else setError(err instanceof Error ? err.message : "Cupinfo kunde inte sparas.");
    }
    finally { setBusy(false); }
  }

  function beginTeamEdit(team:Team) {
    setEditingTeam(team.id);
    setTeamFormOpen(true);
    setTeamDraft({name:team.name,age_class:team.age_class || "",primary_color:team.primary_color || "#111827",secondary_color:team.secondary_color || "#FFFFFF",home_pattern:team.home_pattern||"Helfärgad",home_color_2:team.home_color_2||"#FFFFFF",away_pattern:team.away_pattern||"Helfärgad",away_color_2:team.away_color_2||"#111827",logo_url:team.logo_url||"",logo_source_url:team.logo_source_url||""});
    setKitSuggestion(null);setKitHint("");setAssetFocus("kit");
    setError(""); setMessage("");
  }
  function cancelTeamEdit() { setEditingTeam(null); setTeamFormOpen(false); setTeamDraft(emptyTeam); setKitSuggestion(null); setKitHint(""); setAssetFocus("kit"); }

  useEffect(() => {
    if (!editingTeam) return;
    const frame = window.requestAnimationFrame(() => teamFormRef.current?.scrollIntoView({behavior:"smooth",block:"start"}));
    return () => window.cancelAnimationFrame(frame);
  }, [editingTeam]);

  async function searchAssets(focus:"kit"|"logo",candidate?:KitCandidate) {
    if(!token||!cupId||!teamDraft.name.trim())return;
    setAssetFocus(focus);
    setKitBusy(true);setError("");setMessage("");setKitSuggestion(null);
    try{
      const result=await request<KitSuggestion>(`/api/admin/cups/${cupId}/teams/kit-search`,{method:"POST",body:JSON.stringify({team_name:teamDraft.name,age_class:teamDraft.age_class||null,search_hint:kitHint||null,resolved_club:candidate?[candidate.name,candidate.location,candidate.country].filter(Boolean).join(" · "):null,resolved_source_url:candidate?.source_url||null,search_focus:focus,force_refresh:true})},token);
      setKitSuggestion(result);
      if(result.identity_status!=="ambiguous"&&(focus==="logo"?result.logo_verified:(result.home_verified||result.away_verified))){
        setMessage(focus==="logo"?"Ett verifierat klubbmärke hittades. Granska och välj Använd verifierade uppgifter.":"Verifierade matchställ hittades. Granska källorna innan du använder uppgifterna.");
      }else if(!result.candidate_matches?.length){
        setMessage(focus==="logo"?"Inget säkert klubbmärke hittades. Lägg till klubbens ort eller webbplats och försök igen.":"Ingen säker tröjkälla hittades. Lägg till klubbens ort eller webbplats och försök igen.");
      }
    }catch(err){setError(err instanceof Error?err.message:(focus==="logo"?"Klubbmärket kunde inte sökas.":"Tröjorna kunde inte sökas."));}
    finally{setKitBusy(false);}
  }

  function applyKitSuggestion(){
    if(!kitSuggestion)return;
    setTeamDraft(current=>({...current,
      ...(kitSuggestion.home_verified?{primary_color:kitSuggestion.home_color_1,home_color_2:kitSuggestion.home_color_2,home_pattern:kitSuggestion.home_pattern}:{}),
      ...(kitSuggestion.away_verified?{secondary_color:kitSuggestion.away_color_1,away_color_2:kitSuggestion.away_color_2,away_pattern:kitSuggestion.away_pattern}:{}),
      ...(kitSuggestion.logo_verified?{logo_url:kitSuggestion.logo_url,logo_source_url:kitSuggestion.logo_source_url}:{}),
    }));
    setMessage("De verifierade uppgifterna är införda i formuläret. Spara laget för att bekräfta ändringen.");
  }

  async function searchAllTeamAssets(){
    if(!token||!cupId||!teams.length||bulkKitBusy)return;
    setBulkKitBusy(true);setBulkKitResult("");setBulkKitIssues([]);setError("");setMessage("");let completed=0,saved=0,failed=0,uncertain=0;const updated:Team[]=[];const issues:Array<{teamId:number;teamName:string;reason:string}>=[];
    for(let start=0;start<teams.length;start+=3){
      const batch=teams.slice(start,start+3);
      await Promise.all(batch.map(async team=>{try{
        const suggestion=await request<KitSuggestion>(`/api/admin/cups/${cupId}/teams/kit-search`,{method:"POST",body:JSON.stringify({team_name:team.name,age_class:team.age_class||null,search_focus:"all"})},token);
        const strongKit=suggestion.identity_status==="exact"&&suggestion.confidence==="high"&&(suggestion.home_verified||suggestion.away_verified);if(!strongKit){uncertain++;const identityOk=suggestion.identity_status==="exact";const parts=[!identityOk?"Klubbidentiteten behöver förtydligas.":"Klubbidentitet: verifierad.",suggestion.home_verified?"Hemma: verifierat.":"Hemma: behöver kontrolleras.",suggestion.away_verified?"Borta: verifierat.":"Borta: behöver kontrolleras.",suggestion.logo_verified?"Klubbmärke: verifierat.":""];issues.push({teamId:team.id,teamName:team.name,reason:parts.filter(Boolean).join(" ")});return;}
        const payload={...team,
          ...(suggestion.home_verified?{primary_color:suggestion.home_color_1,home_color_2:suggestion.home_color_2,home_pattern:suggestion.home_pattern}:{}),
          ...(suggestion.away_verified?{secondary_color:suggestion.away_color_1,away_color_2:suggestion.away_color_2,away_pattern:suggestion.away_pattern}:{}),
          ...(suggestion.logo_verified?{logo_url:suggestion.logo_url,logo_source_url:suggestion.logo_source_url}:{}),
        };
        const result=await request<Team>(`/api/admin/cups/${cupId}/teams/${team.id}`,{method:"PUT",body:JSON.stringify(payload)},token);updated.push(result);saved++;
      }catch{failed++;issues.push({teamId:team.id,teamName:team.name,reason:"Sökningen misslyckades. Försök igen individuellt."});}finally{completed++;setBulkKitProgress(`${completed} av ${teams.length} lag kontrollerade`);}}));
    }
    setTeams(current=>current.map(team=>updated.find(item=>item.id===team.id)||team));
    const resultText=`${saved} uppdaterade · ${uncertain} behöver förtydligas · ${failed} misslyckade`;
    setBulkKitResult(resultText);setBulkKitIssues(issues.sort((a,b)=>a.teamName.localeCompare(b.teamName,"sv")));setBulkKitProgress("");setMessage(resultText);
    setBulkKitBusy(false);
  }

  async function saveTeam(event:FormEvent) {
    event.preventDefault();
    if (!token || !cupId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const path = editingTeam ? `/api/admin/cups/${cupId}/teams/${editingTeam}` : `/api/admin/cups/${cupId}/teams`;
      const saved = await request<Team>(path,{method:editingTeam?"PUT":"POST",body:JSON.stringify({...teamDraft,logo_url:normalizedWebUrl(teamDraft.logo_url)})},token);
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
  const canManageCup = isOwner || activeCup?.role === "owner";
  const groupedTeams = teams.filter(team=>team.group_id != null).length;
  const cupinfoReady=Boolean(cupinfo?.name&&cupinfo?.start_date);
  const teamsReady=teams.length>0;
  const groupsReady=teamsReady&&groups.length>0&&groupedTeams===teams.length;
  const isMatchcamp=cupinfo?.arrangement_type==="matchcamp";
  const isPublished=Boolean(activeCup?.is_published);
  const visibleSetupNav=setupNav.filter(([,href])=>{
    if(isMatchcamp)return href!=="#groups"&&href!=="#playoffs";
    return true;
  });
  const scheduleStatus=!scheduleOverview||scheduleOverview.match_count===0?"missing"
    : scheduleOverview.unscheduled_count>0?"incomplete"
      : scheduleOverview.conflict_analysis.error_count>0?"conflicts"
        : scheduleOverview.schedule_dirty?"stale":"current";
  const scheduleReady=scheduleStatus==="current";
  const scheduleStatusLabel=scheduleStatus==="missing"?"Saknas"
    : scheduleStatus==="incomplete"?`${scheduleOverview?.unscheduled_count||0} matcher saknar tid`
      : scheduleStatus==="conflicts"?`${scheduleOverview?.conflict_analysis.error_count||0} blockerande fel`
        : scheduleStatus==="stale"?"Behöver godkännas":"Aktuellt och godkänt";
  const nextTask=!cupinfoReady
    ? {href:"#cupinfo",label:"Komplettera Cupinfo",detail:"Kontrollera cupnamn och datum."}
    : !teamsReady
      ? {href:"#teams",label:"Lägg till lagen",detail:"Registrera lagen och deras matchställ."}
      : !isMatchcamp&&!groupsReady
        ? {href:"#groups",label:"Gör gruppindelningen",detail:`${teams.length-groupedTeams} lag saknar fortfarande grupp.`}
        : scheduleStatus==="missing"
          ? {href:"#schedule",label:"Skapa matchschemat",detail:"Det finns ännu inga matcher att publicera."}
          : scheduleStatus==="incomplete"
            ? {href:"#schedule",label:"Schemalägg alla matcher",detail:`${scheduleOverview?.unscheduled_count||0} matcher saknar tid eller plan.`}
            : scheduleStatus==="conflicts"
              ? {href:"#schedule",label:"Rätta schemakrockarna",detail:`${scheduleOverview?.conflict_analysis.error_count||0} blockerande fel måste lösas.`}
              : scheduleStatus==="stale"
                ? {href:"#schedule",label:"Godkänn det ändrade schemat",detail:"Schemat har ändrats sedan senaste kontrollen."}
                : {href:"#publish",label:"Kontrollera och publicera",detail:"Grunddata och schema är klara för slutkontroll."};
  const checks=[
    {name:"Cupinfo",status:cupinfoReady?"Klar":"Komplettera",href:"#cupinfo",state:cupinfoReady?"done":"next"},
    {name:"Lag",status:teamsReady?`${teams.length} registrerade`:"Saknas",href:"#teams",state:teamsReady?"done":cupinfoReady?"next":"todo"},
    ...(!isMatchcamp?[{name:"Grupper",status:groups.length?`${groupedTeams}/${teams.length} lag placerade`:"Saknas",href:"#groups",state:groupsReady?"done":teamsReady?"next":"todo"}]:[]),
    {name:"Planer & tider",status:scheduleOverview?`${scheduleOverview.pitch_count} ${scheduleOverview.pitch_count===1?"plan":"planer"}`:"Kontrolleras",href:"#venues",state:(isMatchcamp?teamsReady:groupsReady)?"done":"todo"},
    {name:"Schema",status:scheduleStatusLabel,href:"#schedule",state:scheduleReady?"done":(isMatchcamp?teamsReady:groupsReady)?"next":"todo"},
    {name:"Publicering",status:isPublished?"Publicerad":scheduleReady?"Redo för slutkontroll":"Väntar på schema",href:"#publish",state:isPublished?"done":scheduleReady?"next":"todo"},
  ];

  return <main className="admin-workspace">
    <aside className="admin-sidebar">
      <section className="admin-active-cup-card" aria-label="Aktiv cup">
        <div className="admin-sidebar__cup"><span>AKTIV CUP</span><strong>{activeCup?.name || "Ingen cup"}</strong><small>{activeCup?`${activeCup.is_published?"Publicerad":"Utkast"} · ${createdLabel(activeCup.created_at)}`:"Datum saknas"}</small></div>
        {cups.length > 1 && <label className="admin-cup-switcher"><span>Byt cup</span><select value={cupId || ""} onChange={e=>changeCup(Number(e.target.value))}>{cups.map(cup=><option key={cup.id} value={cup.id}>{cup.name} — {createdLabel(cup.created_at)} — {cup.is_published?"PUBLICERAD":"UTKAST"}</option>)}</select></label>}
        {(canManageCup||trashedCups.length>0) && <div className="admin-owner-actions">
          <button className={`admin-trash-button${trashOpen?" is-open":""}`} type="button" onClick={()=>setTrashOpen(value=>!value)}>Papperskorg <span>{trashedCups.length}</span></button>
          {activeCup&&canManageCup && <button className="admin-remove-cup" type="button" disabled={deletingCup} onClick={()=>void removeCup()}>{deletingCup?"Tar bort…":"Ta bort cup"}</button>}
        </div>}
      </section>
      {(canManageCup||trashedCups.length>0) && <>
        {trashOpen && <section className="admin-trash-panel" aria-label="Papperskorg">
          <div className="admin-trash-head"><strong>Papperskorg</strong><span>{trashedCups.length} {trashedCups.length===1?"cup":"cuper"}</span></div>
          {trashedCups.length ? <>
            <div className="admin-trash-list">{trashedCups.map(cup=><div key={cup.id}><span><strong>{cup.name}</strong><small>{cup.start_date || "Datum saknas"}</small></span><button type="button" disabled={busy} onClick={()=>void restoreCup(cup)}>Återställ</button></div>)}</div>
            <button className="admin-empty-trash" type="button" disabled={busy} onClick={()=>void emptyTrash()}>Töm papperskorg</button>
          </> : <p className="admin-trash-empty">Papperskorgen är tom.</p>}
        </section>}
      </>}
      <nav aria-label="Cupadministration">
        <strong className="admin-nav-phase">SKAPA CUPEN</strong>
        {visibleSetupNav.map(([item,href],index)=><a key={item} className={href===`#${activeStep}`?"is-active":""} href={href}><span>{index===0?"00":String(index).padStart(2,"0")}</span>{item}</a>)}
        <strong className="admin-nav-phase">VERKTYG & CUPDRIFT</strong>
        {toolNav.map(([item,href])=><a key={item} className={`admin-nav-tool ${href===`#${activeStep}`?"is-active":""}`} href={href}><span>↗</span>{item}</a>)}
      </nav>
      {publicCup && <a className="admin-public-link" href={publicCup}>Visa publik cup ↗</a>}
      <button className="admin-public-link" type="button" onClick={logout}>Logga ut</button>
    </aside>

    <section className="admin-main" id="overview">
      <header className="admin-pagehead"><div><h1>Cupöversikt</h1></div><div className="admin-pagehead__actions"><span className="admin-draft">{activeCup?.is_published?"PUBLICERAD":"UTKAST"}</span>{publicCup&&<a href={publicCup}>Förhandsgranska <span aria-hidden="true">→</span></a>}</div></header>
      {activeStep==="overview"&&publishedTwin&&<section className="admin-cup-identity-warning" role="alert"><div><span>LIKANDE CUP FINNS REDAN LIVE</span><strong>Du arbetar i utkastet “{activeCup?.name}”</strong><p>Den publicerade cupen “{publishedTwin.name}” är en annan post. Byt cup för att undvika att bygga ett nytt schema ovanpå en dubblett.</p></div><button type="button" disabled={busy} onClick={()=>void changeCup(publishedTwin.id)}>Öppna publicerad cup →</button></section>}
      {activeStep==="overview"&&importWelcome&&<section className="admin-import-welcome" aria-labelledby="import-welcome-title">
        <div className="admin-import-welcome__top"><span>IMPORTEN ÄR KLAR</span><button type="button" onClick={dismissImportWelcome} aria-label="Dölj introduktionen">×</button></div>
        <div className="admin-import-welcome__hero"><div className="admin-import-welcome__check">✓</div><div><h2 id="import-welcome-title">{importWelcome.cupName} är skapad</h2><p>{importWelcome.playoffs?`CupNavi hittade ${importWelcome.playoffs} slutspelsmatcher. Granska och spara trädet innan publicering.`:"CupNavi har redan lagt in underlaget. Du ska granska det som finns – inte importera lagen eller schemat igen."}</p></div></div>
        <div className="admin-import-welcome__facts"><span><b>{importWelcome.teams}</b> lag</span><span><b>{importWelcome.groups}</b> grupper</span><span><b>{importWelcome.matches}</b> matcher</span><span><b>{importWelcome.venues}</b> planer</span>{Boolean(importWelcome.playoffs)&&<span><b>{importWelcome.playoffs}</b> slutspelsmatcher</span>}</div>
        <ol className="admin-import-welcome__steps"><li><b>Kontrollera cupinfo</b><span>Namn, datum, arrangör och adress.</span></li><li><b>Kontrollera planer och schema</b><span>Säkerställ tider, planer och vilopauser.</span></li><li><b>Förhandsgranska och publicera</b><span>Se publikvyn och publicera när allt stämmer.</span></li></ol>
        <div className="admin-import-welcome__actions">{importWelcome.playoffs?<a className="is-primary" href="#playoffs">Granska slutspelet →</a>:<a className="is-primary" href="#cupinfo">Börja med Cupinfo →</a>}<a href="#schedule">Kontrollera schemat</a></div>
      </section>}
      {activeStep==="overview"&&!activeCup?.is_published&&<a className="admin-next-task" href={nextTask.href}><span>NÄSTA UPPGIFT</span><strong>{nextTask.label} →</strong><small>{nextTask.detail}</small></a>}
      {(error||message) && <section className="admin-panel" style={{marginBottom:14}}><strong>{error?"Meddelande":"Klart"}</strong><p>{error||message}</p></section>}
      <section className="admin-dashboard-grid">
        <article className="admin-panel admin-panel--status"><div className="admin-panel__top"><span>STATUS</span><strong>{activeCup?.is_published?"LIVE":"ARBETE PÅGÅR"}</strong></div><h2>{activeCup?.is_published?"Cupen är publicerad":"Vägen till publicering"}</h2><div className="admin-checks">{checks.map(check=><a href={check.href} className={`is-${check.state}`} key={check.name}><span>{check.state==="done"?"✓":check.state==="next"?"→":"○"}</span><strong>{check.name}</strong><small>{check.status}</small></a>)}</div></article>
        <article className="admin-panel admin-panel--codes"><div className="admin-panel__top"><span>KONTO</span><strong>VERIFIERAT</strong></div><h2>Åtkomst</h2><p>{isOwner ? "Ägarkonto med åtkomst till alla cuper." : "Arrangörskonto med åtkomst till tilldelade cuper."}</p><div className="admin-code-placeholder">Konto <b>{account.email}</b></div><div className="admin-code-placeholder">Roll <b>{isOwner ? "ägare" : activeCup?.role || "—"}</b></div></article>
      </section>

      {activeStep==="cupinfo" && <form className="admin-panel admin-cupinfo" id="cupinfo" onSubmit={saveCupInfo}>
        <div className="admin-panel__top"><span>01 / CUPINFO</span><strong>{busy?"ARBETAR":"REDO"}</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Grunduppgifter</h2><p>Uppgifterna för den valda cupen.</p></div><span className="admin-lock">BEHÖRIG</span></div>
        {cupinfo ? <>
          <div className="admin-form-grid">
            <label style={{gridColumn:"1 / -1"}}>Typ av arrangemang<select value={cupinfo.arrangement_type || "tournament"} onChange={e=>{const arrangement_type=e.target.value as CupInfo["arrangement_type"];setCupinfo({...cupinfo,arrangement_type});document.documentElement.dataset.arrangementType=arrangement_type || "tournament";window.dispatchEvent(new CustomEvent("cupnavi:arrangement-type",{detail:arrangement_type}));}}><option value="matchcamp">Matchcamp – matcher utan tabell eller slutspel</option><option value="tournament">Turnering – gruppspel utan slutspel</option><option value="tournament_playoffs">Turnering – gruppspel och slutspel</option><option value="custom">Eget upplägg</option></select><small>Valet anpassar guiden och tar inte bort redan sparad information.</small></label>
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
        <div className="admin-panel__top"><span>02 / LAG</span><strong>{teams.length} REGISTRERADE</strong></div>
        <div className="admin-cupinfo__head"><div><h2>Lag</h2><p>Skapa och redigera lag.</p></div><span className="admin-lock">REDIGERING</span></div>
        {teams.length>0&&<div className="admin-bulk-assets"><div><strong>Tröjor och klubbmärken</strong><span aria-live="polite">{bulkKitProgress||bulkKitResult||"Sök igenom alla lag och spara bara entydigt verifierade träffar."}</span>{bulkKitResult&&<small>Lag som behöver förtydligas söks individuellt med ort eller klubbwebbplats.</small>}</div><button type="button" disabled={bulkKitBusy} onClick={()=>void searchAllTeamAssets()}>{bulkKitBusy?"Söker…":"Sök för alla lag"}</button></div>}{bulkKitIssues.length>0&&<section className="admin-kit-issues"><div><strong>Lag att lösa</strong><span>{bulkKitIssues.length} lag behöver din hjälp</span></div>{bulkKitIssues.map(issue=><article key={issue.teamId}><span><b>{issue.teamName}</b><small>{issue.reason}</small></span><button type="button" onClick={()=>{const team=teams.find(item=>item.id===issue.teamId);if(team){beginTeamEdit(team);setKitHint("");const kitProblem=issue.reason.includes("Hemma: behöver")||issue.reason.includes("Borta: behöver");if(kitProblem){setAssetFocus("kit");window.setTimeout(()=>{document.querySelector(".admin-kit-search")?.scrollIntoView({behavior:"smooth",block:"center"});},80);}else{document.getElementById("teams")?.scrollIntoView({behavior:"smooth",block:"start"});}}}}>{issue.reason.includes("Klubbidentiteten behöver")?"Förtydliga klubb →":issue.reason.includes("Hemma: behöver")||issue.reason.includes("Borta: behöver")?"Kontrollera ställ →":"Försök igen →"}</button></article>)}</section>}
        {(!teams.length || teamFormOpen) && <form ref={teamFormRef} onSubmit={saveTeam} className="admin-team-editor">
          <div className="admin-form-grid">
            <label>Lagnamn<input value={teamDraft.name} onChange={e=>setTeamDraft({...teamDraft,name:e.target.value})} required placeholder="Exempel: ÖSK P2014 Svart" /></label>
            <label>Klass<input value={teamDraft.age_class} onChange={e=>setTeamDraft({...teamDraft,age_class:e.target.value})} placeholder="Exempel: P2014" /></label>
            <section className="admin-kit-editor">
              <div className="admin-kit-editor__head"><TeamKit primary={teamDraft.primary_color} secondary={teamDraft.home_color_2} pattern={teamDraft.home_pattern}/><div><h3>Hemmaställ</h3><p>Välj mönster och tröjfärger.</p></div></div>
              <label>Mönster<select value={teamDraft.home_pattern} onChange={e=>setTeamDraft({...teamDraft,home_pattern:e.target.value as KitPattern})}>{kitPatterns.map(pattern=><option key={pattern}>{pattern}</option>)}</select></label>
              <span className="admin-kit-color-label">Huvudfärg</span><StandardKitColor label="Hemmaställets huvudfärg" value={teamDraft.primary_color} onChange={primary_color=>setTeamDraft({...teamDraft,primary_color})}/>
              {teamDraft.home_pattern!=="Helfärgad"&&<><span className="admin-kit-color-label">Andra färg</span><StandardKitColor label="Hemmaställets andra färg" value={teamDraft.home_color_2} onChange={home_color_2=>setTeamDraft({...teamDraft,home_color_2})}/></>}
            </section>
            <section className="admin-kit-editor">
              <div className="admin-kit-editor__head"><TeamKit primary={teamDraft.secondary_color} secondary={teamDraft.away_color_2} pattern={teamDraft.away_pattern}/><div><h3>Bortaställ</h3><p>Välj ett tydligt alternativ till hemmastället.</p></div></div>
              <label>Mönster<select value={teamDraft.away_pattern} onChange={e=>setTeamDraft({...teamDraft,away_pattern:e.target.value as KitPattern})}>{kitPatterns.map(pattern=><option key={pattern}>{pattern}</option>)}</select></label>
              <span className="admin-kit-color-label">Huvudfärg</span><StandardKitColor label="Bortaställets huvudfärg" value={teamDraft.secondary_color} onChange={secondary_color=>setTeamDraft({...teamDraft,secondary_color})}/>
              {teamDraft.away_pattern!=="Helfärgad"&&<><span className="admin-kit-color-label">Andra färg</span><StandardKitColor label="Bortaställets andra färg" value={teamDraft.away_color_2} onChange={away_color_2=>setTeamDraft({...teamDraft,away_color_2})}/></>}
            </section>
            <div className="admin-logo-editor">
              <span className="admin-logo-preview" aria-hidden="true"><b>CN</b>{teamDraft.logo_url&&<img src={normalizedWebUrl(teamDraft.logo_url)} alt="" referrerPolicy="no-referrer" onError={event=>{event.currentTarget.style.display="none"}} onLoad={event=>{event.currentTarget.style.display="block"}}/>}</span>
              <label>Klubbmärke<small>Ange en direkt bildadress, eller använd sökningen nedan.</small><input type="url" value={teamDraft.logo_url} onChange={e=>setTeamDraft({...teamDraft,logo_url:e.target.value})} onBlur={()=>setTeamDraft(current=>({...current,logo_url:normalizedWebUrl(current.logo_url)}))} placeholder="https://klubb.se/logo.png" /></label>
            </div>
          </div>
          <section className="admin-kit-search" aria-label="Sök lagets matchställ och klubbmärke">
            <div><strong>Sök tröjfärger och mönster eller klubbmärke</strong><span>CupNavi identifierar klubben först och visar sedan verifierade källor. Inget förs in förrän du godkänner träffen.</span></div>
            <label>Sökledtråd <input value={kitHint} onChange={e=>setKitHint(e.target.value)} placeholder="Ort, webbplats eller offentligt Instagramkonto" /></label>
            <div className="admin-asset-search-actions"><button type="button" disabled={kitBusy||!teamDraft.name.trim()} onClick={()=>void searchAssets("kit")}>{kitBusy&&assetFocus==="kit"?"Söker matchställ…":"Sök matchställ"}</button><button type="button" disabled={kitBusy||!teamDraft.name.trim()} onClick={()=>void searchAssets("logo")}>{kitBusy&&assetFocus==="logo"?"Söker klubbmärke…":"Sök klubbmärke"}</button></div>
          </section>
          {kitSuggestion&&!kitSuggestion.found&&!kitSuggestion.home_verified&&!kitSuggestion.away_verified&&<aside className="admin-kit-help"><strong>Hittade vi inte rätt tröja?</strong><ol><li>Skriv klubbens <b>ort</b> i Sökledtråd och sök igen.</li><li>Om namnet är vanligt: klistra in klubbens <b>officiella webbplats</b> eller offentliga Instagram/Facebook-sida.</li><li>Välj rätt klubb om CupNavi visar flera kandidater.</li><li>Finns ingen säker källa: välj tröjfärg och mönster manuellt ovan. CupNavi sparar aldrig en osäker träff automatiskt.</li></ol><small>Tips: skriv hellre “Stångebro United Linköping” eller klubbens webbadress än bara “Stångebro”.</small></aside>}{kitSuggestion&&<section className="admin-kit-result">
            {kitSuggestion.candidate_matches?.length>0&&!kitSuggestion.found&&!kitSuggestion.logo_verified?<><strong>Vilken klubb är rätt?</strong><p>Flera möjliga klubbar hittades. Välj rätt identitet innan uppgifter används.</p><div className="admin-kit-candidates">{kitSuggestion.candidate_matches.map(candidate=><button type="button" key={candidate.source_url} onClick={()=>void searchAssets(assetFocus,candidate)}><b>{candidate.name}</b><span>{[candidate.location,candidate.country].filter(Boolean).join(" · ")}</span><small>{candidate.reason}</small></button>)}</div></>:<><div className="admin-kit-result__head"><div><span>KLUBBIDENTITET · {kitSuggestion.identity_status==="exact"?"VERIFIERAD":kitSuggestion.identity_status==="likely"?"TROLIG":"OSÄKER"}</span><strong>{kitSuggestion.club_match||teamDraft.name}</strong><small>Hemma · {kitSuggestion.home_verified?"verifierat":"kontrollera"} &nbsp; Borta · {kitSuggestion.away_verified?"verifierat":"kontrollera"} &nbsp; Märke · {kitSuggestion.logo_verified?"verifierat":"saknas"}</small></div><button type="button" disabled={!kitSuggestion.home_verified&&!kitSuggestion.away_verified&&!kitSuggestion.logo_verified} onClick={applyKitSuggestion}>Använd verifierade uppgifter</button></div><div className="admin-kit-options">{assetFocus!=="logo"&&<><div><i className="admin-kit-swatch" style={{background:kitBackground(kitSuggestion.home_pattern,kitSuggestion.home_color_1,kitSuggestion.home_color_2)} as CSSProperties}/><span><b>Hemma · {kitSuggestion.home_pattern}</b><small>{kitSuggestion.home_verified?kitSuggestion.home_evidence:"Inte verifierat"}</small></span></div><div><i className="admin-kit-swatch" style={{background:kitBackground(kitSuggestion.away_pattern,kitSuggestion.away_color_1,kitSuggestion.away_color_2)} as CSSProperties}/><span><b>Borta · {kitSuggestion.away_pattern}</b><small>{kitSuggestion.away_verified?kitSuggestion.away_evidence:"Inte verifierat"}</small></span></div></>}{kitSuggestion.logo_verified?<div><img className="admin-kit-logo-result" src={kitSuggestion.logo_url} alt="Hittat klubbmärke" referrerPolicy="no-referrer"/><span><b>Klubbmärke</b><small>Verifierat mot klubbkällan</small></span></div>:assetFocus==="logo"&&<div><span><b>Inget verifierat klubbmärke</b><small>Förtydliga klubbens ort eller officiella webbplats.</small></span></div>}</div><details className="admin-kit-evidence"><summary>Visa varför CupNavi föreslår detta</summary><div className="admin-kit-evidence__grid">{kitSuggestion.home_sources?.length>0&&<section><strong>Hemma</strong><small>{kitSuggestion.home_evidence||"Verifierad källa"}</small>{kitSuggestion.home_sources.map(url=><a key={url} href={url} target="_blank" rel="noreferrer">Öppna bild/källa ↗</a>)}</section>}{kitSuggestion.away_sources?.length>0&&<section><strong>Borta</strong><small>{kitSuggestion.away_evidence||"Verifierad källa"}</small>{kitSuggestion.away_sources.map(url=><a key={url} href={url} target="_blank" rel="noreferrer">Öppna bild/källa ↗</a>)}</section>}{kitSuggestion.logo_source_url&&<section><strong>Klubbmärke</strong><small>Identitetskälla för klubbmärket.</small><a href={kitSuggestion.logo_source_url} target="_blank" rel="noreferrer">Öppna källa ↗</a></section>}</div></details></>}
          </section>}
          <div className="admin-form-footer"><span>{editingTeam?"Du redigerar ett befintligt lag.":""}</span><div className="admin-team-actions">{editingTeam&&<button type="button" onClick={cancelTeamEdit}>Avbryt</button>}<button type="submit" disabled={busy||!teamDraft.name.trim()}>{busy?"Sparar…":editingTeam?"Spara lag":"Lägg till lag"}</button></div></div>
        </form>}
        {teams.length>0&&!teamFormOpen&&<button type="button" className="admin-add-team-compact" onClick={()=>setTeamFormOpen(true)}>＋ Lägg till lag</button>}
        <div className="admin-team-list admin-team-roster">
          {teams.length ? teams.map(team=><article key={team.id} className={editingTeam===team.id?"is-editing":""}>
            <TeamLogo team={team}/>
            <span className="admin-team-kits" aria-label="Hemma- och bortaställ"><span><TeamKit primary={team.primary_color} secondary={team.home_color_2} pattern={team.home_pattern}/><small>Hemma</small></span><span><TeamKit primary={team.secondary_color} secondary={team.away_color_2} pattern={team.away_pattern}/><small>Borta</small></span></span>
            <div className="admin-team-identity"><strong>{team.name}</strong><small><span>{team.age_class||"Klass saknas"}</span><span>{team.group_id?(groups.find(group=>group.id===team.group_id)?.name || `Grupp ${team.group_id}`):"Ej gruppindelat"}</span></small></div>
            <div className="admin-team-actions"><button type="button" onClick={()=>beginTeamEdit(team)}>Redigera</button><button className="is-danger" type="button" onClick={()=>removeTeam(team)}>Ta bort</button></div>
          </article>) : <div className="admin-empty"><strong>Inga lag ännu</strong><span>Lägg till det första laget ovan.</span></div>}
        </div>
        {teams.length>0&&<div className="admin-step-complete"><span>Alla lag inlagda och kontrollerade?</span><a href={isMatchcamp?"#venues":"#groups"}>Klar med lag → {isMatchcamp?"Planer & tider":"Grupper"}</a></div>}
      </section>}

      {activeStep==="groups" && <section className="admin-panel admin-teams" id="groups">
        <div className="admin-panel__top"><span>03 / GRUPPER</span><strong>{groups.length} GRUPPER · {groupedTeams}/{teams.length} LAG</strong></div>
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
      {activeStep==="access" && token && cupId && account && <AccessAdmin token={token} cupId={cupId} accountId={account.id} isPlatformOwner={isOwner}/>}

      {activeStep==="export" && token && cupId && <ExportAdmin token={token} cupId={cupId}/>}
    </section>
    {children}
  </main>;
}
