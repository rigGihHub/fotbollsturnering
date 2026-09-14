"use client";

import { useEffect, useRef, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";

type State = "checking" | "online" | "waiting" | "recovering";

export default function AdminWorkspaceResilient() {
  const [state, setState] = useState<State>("checking");
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const stableToken = useRef<string | null>(null);
  const allowLogout = useRef(false);

  useEffect(() => {
    stableToken.current = localStorage.getItem(TOKEN_KEY);

    const markExplicitLogout = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest("button") : null;
      if (target?.textContent?.trim() === "Logga ut") allowLogout.current = true;
    };
    document.addEventListener("click", markExplicitLogout, true);

    let cancelled = false;
    let healthTimer: ReturnType<typeof setTimeout> | null = null;
    let sessionTimer: ReturnType<typeof setInterval> | null = null;

    async function checkHealth() {
      try {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 6500);
        const response = await fetch(`${CLIENT_API_BASE}/health`, { cache: "no-store", signal: controller.signal });
        window.clearTimeout(timeout);
        if (response.ok) {
          if (!cancelled) setState("online");
          return;
        }
      } catch {
        // Render free instances may still be starting.
      }
      if (!cancelled) {
        setState("waiting");
        healthTimer = setTimeout(checkHealth, 2200);
      }
    }

    void checkHealth();

    sessionTimer = window.setInterval(() => {
      if (cancelled || allowLogout.current) return;
      const current = localStorage.getItem(TOKEN_KEY);
      const known = stableToken.current;
      if (current) {
        stableToken.current = current;
        return;
      }
      if (!known) return;

      // AdminWorkspace historically cleared the token on any failed session
      // restore. Treat that as transient unless the user explicitly logged out.
      setState("recovering");
      localStorage.setItem(TOKEN_KEY, known);
      window.setTimeout(() => {
        if (cancelled || allowLogout.current) return;
        setWorkspaceKey(value => value + 1);
        setState("online");
      }, 80);
    }, 120);

    return () => {
      cancelled = true;
      document.removeEventListener("click", markExplicitLogout, true);
      if (healthTimer) clearTimeout(healthTimer);
      if (sessionTimer) clearInterval(sessionTimer);
    };
  }, []);

  if (state === "online") return <AdminWorkspace key={workspaceKey} />;

  return (
    <main className="admin-main admin-starting" aria-live="polite">
      <section className="admin-panel">
        <div className="admin-panel__top"><span>CUPNAVI</span><strong>{state === "recovering" ? "ÅTERSTÄLLER SESSION" : "ANSLUTER"}</strong></div>
        <h2>{state === "recovering" ? "Behåller din inloggning" : "Startar administrationen"}</h2>
        <p>{state === "recovering" ? "Ett tillfälligt API-fel avbröt sessionskontrollen. CupNavi behåller din inloggning och öppnar admin igen automatiskt." : "Din inloggning ligger kvar. CupNavi väntar tills servern är redo innan admin öppnas."}</p>
      </section>
    </main>
  );
}
