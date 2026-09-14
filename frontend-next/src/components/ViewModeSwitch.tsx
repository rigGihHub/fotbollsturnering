"use client";

import { useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const CUP_KEY = "cupnavi_admin_active_cup_v651";

type Cup = { id:number; public_slug?:string|null };
type SessionPayload = { cups?:Cup[] };

export function ViewModeSwitch() {
  const [path,setPath] = useState("");
  const [hasSession,setHasSession] = useState(false);
  const [opening,setOpening] = useState(false);

  useEffect(() => {
    setPath(window.location.pathname);
    setHasSession(Boolean(localStorage.getItem(TOKEN_KEY)));
  }, []);

  const inAdmin = path.startsWith("/admin");
  const inCup = path.startsWith("/cup/");
  if (!inAdmin && !inCup) return null;
  if (inCup && !hasSession) return null;

  async function openTournament() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      window.location.href = "/admin";
      return;
    }
    setOpening(true);
    try {
      const response = await fetch(`${CLIENT_API_BASE}/api/admin/session`, {
        headers:{Authorization:`Bearer ${token}`},
        cache:"no-store",
      });
      if (!response.ok) throw new Error("session");
      const payload = await response.json() as SessionPayload;
      const cups = payload.cups || [];
      const storedId = Number(localStorage.getItem(CUP_KEY));
      const active = cups.find(cup => cup.id === storedId) || cups[0];
      if (active?.public_slug) {
        window.location.href = `/cup/${active.public_slug}`;
        return;
      }
      window.location.href = "/admin";
    } catch {
      window.location.href = "/admin";
    }
  }

  return (
    <div style={{position:"fixed",right:12,bottom:inCup?76:12,zIndex:10000,display:"flex",gap:8,padding:6,border:"1px solid rgba(17,24,39,.18)",borderRadius:14,background:"rgba(255,255,255,.94)",boxShadow:"0 8px 28px rgba(15,23,42,.16)",backdropFilter:"blur(10px)"}}>
      {inAdmin ? (
        <button type="button" onClick={()=>void openTournament()} disabled={opening} style={{border:0,borderRadius:10,padding:"10px 13px",fontWeight:800,background:"#111827",color:"white",fontSize:13}}>
          {opening?"Öppnar…":"⚽ Turneringsvy"}
        </button>
      ) : (
        <a href="/admin" style={{borderRadius:10,padding:"10px 13px",fontWeight:800,background:"#111827",color:"white",fontSize:13,textDecoration:"none"}}>⚙ Admin</a>
      )}
    </div>
  );
}
