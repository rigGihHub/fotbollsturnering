"use client";

import { useCallback, useEffect, useState } from "react";
import ImportAdmin from "./import-admin";
import PublishReportingAdmin from "./publish-reporting-admin";
import RosterAdmin from "./roster-admin";
import RoleCodeAdmin from "./role-code-admin";
import RefereeRoleCodeAdmin from "./referee-role-code-admin";
import TeamRoleCodeAdmin from "./team-role-code-admin";
import { CLIENT_API_BASE } from "../lib/client-api";

const API = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Cup = { id:number; name:string; role:string; public_slug?:string|null };
type SessionPayload = { cups:Cup[] };

function requestedCupId(cups:Cup[]) {
  const query = Number(new URLSearchParams(window.location.search).get("cup"));
  const stored = Number(localStorage.getItem(CUP_KEY));
  const candidate = query || stored;
  return cups.some(cup => cup.id === candidate) ? candidate : (cups[0]?.id ?? null);
}

export default function AdminOperations() {
  const [token,setToken] = useState<string|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [cupId,setCupId] = useState<number|null>(null);
  const [error,setError] = useState("");

  const load = useCallback(async () => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (!storedToken) {
      setToken(null); setCups([]); setCupId(null); setError("");
      return;
    }

    // Keep the last known-good operational state during transient network or
    // server errors. Only a verified 401 is allowed to invalidate auth here.
    try {
      const response = await fetch(`${API}/api/admin/session`, {
        headers:{Authorization:`Bearer ${storedToken}`},
        cache:"no-store",
      });
      const payload = await response.json().catch(() => null) as SessionPayload | {detail?:string} | null;

      if (response.status === 401) {
        setToken(null); setCups([]); setCupId(null);
        setError("Sessionen är inte längre giltig. Logga in igen.");
        return;
      }
      if (!response.ok) {
        const detail = payload && "detail" in payload && payload.detail ? payload.detail : `API-fel ${response.status}`;
        throw new Error(detail);
      }

      const session = payload as SessionPayload;
      const available = session.cups || [];
      setToken(storedToken);
      setCups(available);
      setCupId(requestedCupId(available));
      setError("");
    } catch (err) {
      // A Render cold start, timeout or 5xx must not blank operational modules
      // or create the visual impression that the user was logged out.
      if (!token) setToken(storedToken);
      setError(err instanceof Error ? `Tillfälligt anslutningsproblem: ${err.message}` : "Tillfälligt anslutningsproblem.");
    }
  },[token]);

  useEffect(() => {
    void load();
    const refresh = () => { void load(); };
    window.addEventListener("storage", refresh);
    window.addEventListener("focus", refresh);
    const timer = window.setInterval(() => {
      if (!cups.length) return;
      const next = requestedCupId(cups);
      setCupId(current => current === next ? current : next);
    }, 800);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("focus", refresh);
      window.clearInterval(timer);
    };
  },[load,cups]);

  if (!token || !cupId) {
    if (!error) return null;
    return <section className="admin-main"><section className="admin-panel"><strong>Operativa moduler kunde inte laddas</strong><p>{error}</p></section></section>;
  }

  const activeCup=cups.find(cup=>cup.id===cupId)||null;
  return <section className="admin-main admin-operations-flow" aria-label="Operativa cupmoduler">
    {error && <section className="admin-panel" style={{marginBottom:14}}><strong>Återansluter</strong><p>{error}</p></section>}
    <section className="admin-panel admin-flow-context" style={{marginBottom:14}}>
      <div className="admin-panel__top"><span>FORTSÄTT MED CUPEN</span><strong>AKTIV CUP · {activeCup?.role?.toUpperCase()}</strong></div>
      <div className="admin-flow-context__title">
        <div><h2>{activeCup?.name || "Cup"}</h2><p>Samma aktiva cup används nu i hela admin. Du behöver inte välja cup en gång till här.</p></div>
        <span className="admin-lock">SYNKAD</span>
      </div>
      <nav className="admin-flow-jumps" aria-label="Snabblänkar till cupens fortsatta arbete">
        <a href="#access-flow">Behörighet</a>
        <a href="#roster-flow">Trupper</a>
        <a href="#publish">Publicering</a>
        <a href="#reporting">Rapportering</a>
        <a href="#import">Import</a>
      </nav>
    </section>
    <div id="access-flow" className="admin-flow-group">
      <div className="admin-flow-group__label"><span>01</span><div><strong>Behörighet</strong><small>Koder för rapportör, domare och lagportal.</small></div></div>
      <RoleCodeAdmin token={token} cupId={cupId} publicSlug={activeCup?.public_slug}/>
      <RefereeRoleCodeAdmin token={token} cupId={cupId} publicSlug={activeCup?.public_slug}/>
      <TeamRoleCodeAdmin token={token} cupId={cupId} publicSlug={activeCup?.public_slug}/>
    </div>
    <div id="roster-flow" className="admin-flow-group">
      <div className="admin-flow-group__label"><span>02</span><div><strong>Trupper</strong><small>Spelare och lagens trupparbete.</small></div></div>
      <RosterAdmin token={token} cupId={cupId}/>
    </div>
    <div className="admin-flow-group">
      <div className="admin-flow-group__label"><span>03</span><div><strong>Publicera & rapportera</strong><small>Kontrollera cupen, publicera och rapportera matcher.</small></div></div>
      <PublishReportingAdmin token={token} cupId={cupId}/>
    </div>
    <div className="admin-flow-group">
      <div className="admin-flow-group__label"><span>04</span><div><strong>Import</strong><small>Uppdatera cupen från nytt underlag utan tysta överskrivningar.</small></div></div>
      <ImportAdmin token={token} cupId={cupId}/>
    </div>
  </section>;
}
