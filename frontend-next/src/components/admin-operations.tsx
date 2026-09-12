"use client";

import { useCallback, useEffect, useState } from "react";
import ImportAdmin from "./import-admin";
import PublishReportingAdmin from "./publish-reporting-admin";
import { CLIENT_API_BASE } from "../lib/client-api";

const API = CLIENT_API_BASE;
const TOKEN_KEY = "cupnavi_admin_session_v629";

type Cup = { id:number; name:string; role:string };
type SessionPayload = { cups:Cup[] };

export default function AdminOperations() {
  const [token,setToken] = useState<string|null>(null);
  const [cups,setCups] = useState<Cup[]>([]);
  const [cupId,setCupId] = useState<number|null>(null);
  const [error,setError] = useState("");

  const load = useCallback(async () => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setToken(null); setCups([]); setCupId(null); setError("");
      return;
    }
    try {
      const response = await fetch(`${API}/api/admin/session`, {
        headers:{Authorization:`Bearer ${stored}`},
        cache:"no-store",
      });
      const payload = await response.json().catch(() => null) as SessionPayload | {detail?:string} | null;
      if (!response.ok) throw new Error(payload && "detail" in payload && payload.detail ? payload.detail : `API-fel ${response.status}`);
      const session = payload as SessionPayload;
      const available = session.cups || [];
      setToken(stored);
      setCups(available);
      setCupId(current => current && available.some(cup => cup.id === current) ? current : (available[0]?.id ?? null));
      setError("");
    } catch (err) {
      setToken(null); setCups([]); setCupId(null);
      setError(err instanceof Error ? err.message : "De operativa modulerna kunde inte läsa arrangörssessionen.");
    }
  },[]);

  useEffect(() => {
    void load();
    const refresh = () => { void load(); };
    window.addEventListener("storage", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("focus", refresh);
    };
  },[load]);

  if (!token || !cupId) {
    if (!error) return null;
    return <section className="admin-main"><section className="admin-panel"><strong>Operativa moduler kunde inte laddas</strong><p>{error}</p></section></section>;
  }

  return <section className="admin-main" aria-label="Operativa cupmoduler">
    <section className="admin-panel" style={{marginBottom:14}}>
      <div className="admin-panel__top"><span>OPERATIV CUP</span><strong>SERVERVERIFIERAD ÅTKOMST</strong></div>
      <label>Publicering, rapportering och import för
        <select value={cupId} onChange={event=>setCupId(Number(event.target.value))} style={{marginLeft:10}}>
          {cups.map(cup=><option key={cup.id} value={cup.id}>{cup.name} · {cup.role}</option>)}
        </select>
      </label>
      <p>Valet är separat och synligt så att inga skrivningar kan råka gå till en annan cup än den som visas här.</p>
    </section>
    <PublishReportingAdmin token={token} cupId={cupId}/>
    <ImportAdmin token={token} cupId={cupId}/>
  </section>;
}
