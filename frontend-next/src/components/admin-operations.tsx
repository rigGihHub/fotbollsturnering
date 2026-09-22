"use client";

import { useEffect, useState } from "react";
import ImportAdmin from "./import-admin";
import PublishReportingAdmin from "./publish-reporting-admin";
import RosterAdmin from "./roster-admin";
import RoleCodeAdmin from "./role-code-admin";
import TeamRoleCodeAdmin from "./team-role-code-admin";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const VERIFIED_PERSISTENT_CACHE_KEY = "cupnavi_admin_verified_persistent_v1";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Cup = { id:number; name:string; role:string; public_slug?:string|null };
type VerifiedCache = { token:string; cups:Cup[]; verifiedAt:number };
type HeavyStep = "publish"|"reporting"|"import"|"other";

function requestedCupId(cups:Cup[]) {
  const query = Number(new URLSearchParams(window.location.search).get("cup"));
  const stored = Number(localStorage.getItem(CUP_KEY));
  const candidate = query || stored;
  return cups.some(cup => cup.id === candidate) ? candidate : (cups[0]?.id ?? null);
}

function readVerified():VerifiedCache|null {
  const storedToken=localStorage.getItem(TOKEN_KEY);
  if(!storedToken)return null;
  for (const [storage,key] of [[sessionStorage,VERIFIED_CACHE_KEY],[localStorage,VERIFIED_PERSISTENT_CACHE_KEY]] as const) {
    try {
      const raw=storage.getItem(key);
      if(!raw)continue;
      const parsed=JSON.parse(raw) as VerifiedCache;
      if(parsed.token===storedToken&&Array.isArray(parsed.cups))return parsed;
    } catch {}
  }
  return null;
}

function activeHeavyStep():HeavyStep {
  const hash=window.location.hash.replace(/^#/,"");
  if(hash==="publish")return "publish";
  if(hash==="reporting")return "reporting";
  if(hash==="import")return "import";
  return "other";
}

export default function AdminOperations() {
  const [token,setToken] = useState<string|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [cupId,setCupId] = useState<number|null>(null);
  const [step,setStep] = useState<HeavyStep>("other");

  useEffect(() => {
    const sync = () => {
      const verified=readVerified();
      if(verified){
        setToken(verified.token);
        setCups(verified.cups || []);
        setCupId(requestedCupId(verified.cups || []));
      }
      setStep(activeHeavyStep());
    };
    const onStep=(event:Event)=>{
      const detail=(event as CustomEvent<string>).detail;
      if(detail==="publish"||detail==="reporting"||detail==="import")setStep(detail);
      else setStep("other");
    };
    sync();
    window.addEventListener("storage",sync);
    window.addEventListener("cupnavi:session-refresh",sync);
    window.addEventListener("hashchange",sync);
    window.addEventListener("cupnavi:admin-step",onStep);
    return()=>{
      window.removeEventListener("storage",sync);
      window.removeEventListener("cupnavi:session-refresh",sync);
      window.removeEventListener("hashchange",sync);
      window.removeEventListener("cupnavi:admin-step",onStep);
    };
  },[]);

  if (!token || !cupId || step==="other") return null;

  const activeCup=cups.find(cup=>cup.id===cupId)||null;

  if(step==="import") {
    return <section className="admin-main admin-operations-flow" aria-label="Import">
      <div className="admin-flow-group">
        <div className="admin-flow-group__label"><span>↗</span><div><strong>Uppdatera från fil</strong><small>Frivilligt verktyg när ett redan sparat underlag faktiskt har ändrats.</small></div></div>
        <ImportAdmin token={token} cupId={cupId}/>
      </div>
    </section>;
  }

  return <section className="admin-main admin-operations-flow" aria-label={step==="publish"?"Publicering":"Matchrapportering"}>
    <section className="admin-panel admin-flow-context" style={{marginBottom:14}}>
      <div className="admin-panel__top"><span>{step==="publish"?"STEG 8 · KONTROLL & PUBLICERING":"VERKTYG · MATCHRAPPORTERING"}</span><strong>AKTIV CUP · {activeCup?.role?.toUpperCase()}</strong></div>
      <div className="admin-flow-context__title"><div><h2>{activeCup?.name || "Cup"}</h2><p>{step==="publish"?"Kontrollera blockerare, förhandsgranska och publicera när allt stämmer.":"Förbered behörigheter och resultatrapportering inför cupdagen."}</p></div><span className="admin-lock">{step==="publish"?"SLUTKONTROLL":"CUPDRIFT"}</span></div>
    </section>
    {step==="reporting" && <>
      <div id="access-flow" className="admin-flow-group">
        <div className="admin-flow-group__label"><span>A</span><div><strong>Behörighet</strong><small>En gemensam rapportörskod för resultat och separata lagkoder för trupper.</small></div></div>
        <RoleCodeAdmin token={token} cupId={cupId} publicSlug={activeCup?.public_slug}/>
        <TeamRoleCodeAdmin token={token} cupId={cupId} publicSlug={activeCup?.public_slug}/>
      </div>
      <div id="roster-flow" className="admin-flow-group">
        <div className="admin-flow-group__label"><span>B</span><div><strong>Trupper</strong><small>Spelare och lagens trupparbete.</small></div></div>
        <RosterAdmin token={token} cupId={cupId}/>
      </div>
    </>}
    <div className="admin-flow-group">
      <PublishReportingAdmin token={token} cupId={cupId} mode={step} publicSlug={activeCup?.public_slug}/>
    </div>
  </section>;
}
