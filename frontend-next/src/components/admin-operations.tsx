"use client";

import { useEffect, useState } from "react";
import ImportAdmin from "./import-admin";
import PublishReportingAdmin from "./publish-reporting-admin";
import RosterAdmin from "./roster-admin";
import RoleCodeAdmin from "./role-code-admin";
import RefereeRoleCodeAdmin from "./referee-role-code-admin";
import TeamRoleCodeAdmin from "./team-role-code-admin";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Cup = { id:number; name:string; role:string; public_slug?:string|null };
type VerifiedCache = { token:string; cups:Cup[]; verifiedAt:number };

function requestedCupId(cups:Cup[]) {
  const query = Number(new URLSearchParams(window.location.search).get("cup"));
  const stored = Number(localStorage.getItem(CUP_KEY));
  const candidate = query || stored;
  return cups.some(cup => cup.id === candidate) ? candidate : (cups[0]?.id ?? null);
}

function readVerified():VerifiedCache|null {
  try {
    const raw=sessionStorage.getItem(VERIFIED_CACHE_KEY);
    if(!raw)return null;
    const parsed=JSON.parse(raw) as VerifiedCache;
    const storedToken=localStorage.getItem(TOKEN_KEY);
    if(!storedToken||parsed.token!==storedToken||!Array.isArray(parsed.cups))return null;
    return parsed;
  } catch { return null; }
}

export default function AdminOperations() {
  const [token,setToken] = useState<string|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [cupId,setCupId] = useState<number|null>(null);

  useEffect(() => {
    const sync = () => {
      const verified=readVerified();
      if(!verified){return;}
      setToken(verified.token);
      setCups(verified.cups || []);
      setCupId(requestedCupId(verified.cups || []));
    };
    sync();
    window.addEventListener("storage",sync);
    window.addEventListener("cupnavi:session-refresh",sync);
    const timer=window.setInterval(()=>{
      const verified=readVerified();
      if(!verified)return;
      setCupId(current=>{
        const next=requestedCupId(verified.cups || []);
        return current===next?current:next;
      });
    },1200);
    return()=>{
      window.removeEventListener("storage",sync);
      window.removeEventListener("cupnavi:session-refresh",sync);
      window.clearInterval(timer);
    };
  },[]);

  if (!token || !cupId) return null;

  const activeCup=cups.find(cup=>cup.id===cupId)||null;
  return <section className="admin-main admin-operations-flow" aria-label="Operativa cupmoduler">
    <section className="admin-panel admin-flow-context" style={{marginBottom:14}}>
      <div className="admin-panel__top"><span>FORTSÄTT MED CUPEN</span><strong>AKTIV CUP · {activeCup?.role?.toUpperCase()}</strong></div>
      <div className="admin-flow-context__title">
        <div><h2>{activeCup?.name || "Cup"}</h2><p>Samma aktiva cup används i hela admin.</p></div>
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
