"use client";

import { useEffect, useRef, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import AdminOperations from "./admin-operations";
import AdminStepFlow from "./admin-step-flow";
import CupCreateLauncher from "./cup-create-launcher-resilient";
import ApiWakeGuard from "./api-wake-guard";
import PlayoffImportReview from "./playoff-import-review";
import PitchWindowImportReview from "./pitch-window-import-review";
import ImportCompletionSummary from "./import-completion-summary";
import ImportRecoveryGuard from "./import-recovery-guard";
import { CLIENT_API_BASE } from "../lib/client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const BACKGROUND_KEY = "cupnavi_admin_last_background_v1";
const MOBILE_RESUME_GRACE_MS = 30_000;
const UNAUTHORIZED_CONFIRMATIONS = 2;

type AuthState = "checking" | "authenticated" | "unauthenticated" | "waiting";

export default function AdminAuthShell() {
  const [state, setState] = useState<AuthState>("checking");
  const [authKey, setAuthKey] = useState(0);
  const retryRef = useRef<number | null>(null);
  const lastTokenRef = useRef<string | null>(null);
  const unauthorizedRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    function recentlyResumed() {
      try {
        const raw = sessionStorage.getItem(BACKGROUND_KEY);
        const when = Number(raw || 0);
        return when > 0 && Date.now() - when < MOBILE_RESUME_GRACE_MS;
      } catch {
        return false;
      }
    }

    function scheduleVerify(delay:number) {
      if (cancelled) return;
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
      retryRef.current = window.setTimeout(() => void verify(), delay);
    }

    async function verify() {
      if (cancelled) return;
      if (document.visibilityState === "hidden") {
        scheduleVerify(1200);
        return;
      }

      const token = localStorage.getItem(TOKEN_KEY);
      lastTokenRef.current = token;

      if (!token) {
        unauthorizedRef.current = 0;
        setState("unauthenticated");
        return;
      }

      // Once admin is authenticated, never unmount the working UI just because
      // a background revalidation starts. Camera/file pickers temporarily hide
      // the page on mobile and destroying the tree here loses in-progress work.
      setState(current => current === "authenticated" ? current : "checking");
      try {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 9000);
        const response = await fetch(`${CLIENT_API_BASE}/api/admin/session`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
          signal: controller.signal,
        });
        window.clearTimeout(timeout);

        if (response.status === 401) {
          unauthorizedRef.current += 1;
          const inResumeGrace = recentlyResumed();
          if (inResumeGrace || unauthorizedRef.current < UNAUTHORIZED_CONFIRMATIONS) {
            // Preserve authenticated children while confirming the 401. A single
            // stale/mobile-resume response must not wipe forms, imports or modals.
            setState(current => current === "authenticated" ? current : "waiting");
            scheduleVerify(inResumeGrace ? 2500 : 900);
            return;
          }
          localStorage.removeItem(TOKEN_KEY);
          unauthorizedRef.current = 0;
          if (!cancelled) setState("unauthenticated");
          return;
        }

        if (!response.ok) throw new Error(`session ${response.status}`);
        unauthorizedRef.current = 0;
        try { sessionStorage.removeItem(BACKGROUND_KEY); } catch {}
        if (!cancelled) setState("authenticated");
      } catch {
        if (cancelled) return;
        unauthorizedRef.current = 0;
        // Same rule for timeouts/5xx/offline: keep authenticated UI mounted.
        setState(current => current === "authenticated" ? current : "waiting");
        scheduleVerify(1800);
      }
    }

    void verify();

    const tokenWatcher = window.setInterval(() => {
      if (cancelled) return;
      const token = localStorage.getItem(TOKEN_KEY);
      if (token === lastTokenRef.current) return;
      lastTokenRef.current = token;
      unauthorizedRef.current = 0;
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
      setAuthKey(value => value + 1);
    }, 700);

    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        try { sessionStorage.setItem(BACKGROUND_KEY, String(Date.now())); } catch {}
        return;
      }
      if (localStorage.getItem(TOKEN_KEY)) scheduleVerify(350);
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(tokenWatcher);
      if (retryRef.current !== null) window.clearTimeout(retryRef.current);
    };
  }, [authKey]);

  if (state === "checking" || state === "waiting") {
    return (
      <main className="admin-main admin-starting" aria-live="polite">
        <section className="admin-panel">
          <div className="admin-panel__top"><span>CUPNAVI</span><strong>{state === "waiting" ? "ÅTERANSLUTER" : "KONTROLLERAR SESSION"}</strong></div>
          <h2>{state === "waiting" ? "Återansluter utan att logga ut dig" : "Öppnar administrationen"}</h2>
          <p>{state === "waiting" ? "Din sparade inloggning ligger kvar medan CupNavi kontrollerar anslutningen igen." : "CupNavi verifierar din session innan admin visas."}</p>
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
      <PitchWindowImportReview/>
      <PlayoffImportReview/>
      <ImportCompletionSummary/>
      <AdminWorkspace key={`admin-${authKey}`} />
      <AdminOperations/>
    </>
  );
}
