"use client";

import { useEffect, useRef, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import AdminOperations from "./admin-operations";
import AdminStepFlow from "./admin-step-flow";
import CupCreateLauncher from "./cup-create-launcher-resilient";
import CupSetupGuide from "./cup-setup-guide";
import ApiWakeGuard from "./api-wake-guard";
import PlayoffImportReview from "./playoff-import-review";
import PitchWindowImportReview from "./pitch-window-import-review";
import ImportCompletionSummary from "./import-completion-summary";
import ImportRecoveryGuard from "./import-recovery-guard";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";

type AuthState = "checking" | "authenticated" | "unauthenticated" | "waiting";

export default function AdminAuthShell() {
  const [state, setState] = useState<AuthState>("checking");
  const [authKey, setAuthKey] = useState(0);
  const retryRef = useRef<number | null>(null);
  const lastTokenRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (cancelled) return;
      const token = localStorage.getItem(TOKEN_KEY);
      lastTokenRef.current = token;

      if (!token) {
        setState("unauthenticated");
        return;
      }

      setState(current => current === "authenticated" ? current : "checking");
      try {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 7000);
        const response = await fetch(`${CLIENT_API_BASE}/api/admin/session`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
          signal: controller.signal,
        });
        window.clearTimeout(timeout);

        if (response.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          if (!cancelled) setState("unauthenticated");
          return;
        }
        if (!response.ok) throw new Error(`session ${response.status}`);
        if (!cancelled) setState("authenticated");
      } catch {
        if (cancelled) return;
        setState("waiting");
        retryRef.current = window.setTimeout(verify, 1800);
      }
    }

    void verify();

    const tokenWatcher = window.setInterval(() => {
      if (cancelled) return;
      const token = localStorage.getItem(TOKEN_KEY);
      if (token === lastTokenRef.current) return;
      lastTokenRef.current = token;
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
      setAuthKey(value => value + 1);
    }, 500);

    return () => {
      cancelled = true;
      window.clearInterval(tokenWatcher);
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
    };
  }, [authKey]);

  if (state === "checking" || state === "waiting") {
    return (
      <main className="admin-main admin-starting" aria-live="polite">
        <section className="admin-panel">
          <div className="admin-panel__top"><span>CUPNAVI</span><strong>{state === "waiting" ? "ÅTERANSLUTER" : "KONTROLLERAR SESSION"}</strong></div>
          <h2>{state === "waiting" ? "Servern svarar inte ännu" : "Öppnar administrationen"}</h2>
          <p>{state === "waiting" ? "Din sparade inloggning ändras inte. CupNavi försöker ansluta igen automatiskt." : "CupNavi verifierar din session innan admin visas."}</p>
        </section>
      </main>
    );
  }

  if (state === "unauthenticated") {
    return <><ApiWakeGuard/><AdminWorkspace key={`login-${authKey}`} /></>;
  }

  return (
    <>
      <ApiWakeGuard/>
      <ImportRecoveryGuard/>
      <CupCreateLauncher/>
      <AdminStepFlow/>
      <CupSetupGuide/>
      <PitchWindowImportReview/>
      <PlayoffImportReview/>
      <ImportCompletionSummary/>
      <AdminWorkspace key={`admin-${authKey}`} />
      <AdminOperations/>
    </>
  );
}
