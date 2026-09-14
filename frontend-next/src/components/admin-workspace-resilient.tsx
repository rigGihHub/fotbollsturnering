"use client";

import { useEffect, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import { CLIENT_API_BASE } from "../lib/client-api";

type State = "checking" | "online" | "waiting";

export default function AdminWorkspaceResilient() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function check() {
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
        timer = setTimeout(check, 2200);
      }
    }

    void check();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (state === "online") return <AdminWorkspace />;

  return (
    <main className="admin-main admin-starting" aria-live="polite">
      <section className="admin-panel">
        <div className="admin-panel__top"><span>CUPNAVI</span><strong>ANSLUTER</strong></div>
        <h2>Startar administrationen</h2>
        <p>Din inloggning ligger kvar. CupNavi väntar tills servern är redo innan admin öppnas.</p>
      </section>
    </main>
  );
}
