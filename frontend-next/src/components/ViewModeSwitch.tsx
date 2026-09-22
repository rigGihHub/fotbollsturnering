"use client";

import { useEffect, useState } from "react";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Cup = { id:number; public_slug?:string|null };
type VerifiedCache = { token?:string; cups?:Cup[] };

function verifiedCups():Cup[] {
  try {
    const raw=sessionStorage.getItem(VERIFIED_CACHE_KEY);
    if(!raw)return [];
    const parsed=JSON.parse(raw) as VerifiedCache;
    const token=localStorage.getItem(TOKEN_KEY);
    if(!token||parsed.token!==token)return [];
    return parsed.cups || [];
  } catch { return []; }
}

export function ViewModeSwitch() {
  const [path,setPath] = useState("");
  const [hasSession,setHasSession] = useState(false);
  const [opening,setOpening] = useState(false);
  const [reporterLink,setReporterLink] = useState("/reporter");

  useEffect(() => {
    setPath(window.location.pathname);
    setHasSession(Boolean(localStorage.getItem(TOKEN_KEY)));
    if(window.location.pathname.startsWith("/cup/"))setReporterLink(`/reporter?returnTo=${encodeURIComponent(window.location.pathname+window.location.search)}`);
  }, []);

  const inAdmin = path.startsWith("/admin");
  const inCup = path.startsWith("/cup/");
  if (!inAdmin && !inCup) return null;
  if (inCup && !hasSession) return null;

  function openTournament() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      window.location.href = "/admin";
      return;
    }
    setOpening(true);
    const cups=verifiedCups();
    const storedId = Number(localStorage.getItem(CUP_KEY));
    const active = cups.find(cup => cup.id === storedId) || cups[0];
    if (active?.public_slug) {
      window.location.href = `/cup/${active.public_slug}?preview=1&cup=${active.id}`;
      return;
    }
    window.location.href = "/admin";
  }

  return (
    <div className={`view-mode-switch ${inCup?"is-public":"is-admin"}`}>
      {inAdmin ? (
        <button type="button" onClick={openTournament} disabled={opening}>
          {opening?"Öppnar…":"Turneringsvy"}
        </button>
      ) : (
        <><a href={reporterLink} className="reporting-shortcut">Rapportering</a><a href="/admin">Admin</a></>
      )}
    </div>
  );
}
