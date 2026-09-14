"use client";

import { useEffect, useRef, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import AdminOperations from "./admin-operations";
import AdminStepFlow from "./admin-step-flow";
import AdminLazyExtras from "./admin-lazy-extras";
import CupCreateLauncher from "./cup-create-launcher-resilient";
import ApiWakeGuard from "./api-wake-guard";
import ImportRecoveryGuard from "./import-recovery-guard";
import { CLIENT_API_BASE } from "../lib/client-api";
import {
  authoritativeAdminSessionFetch,
  installAdminSessionFetchGate,
} from "../lib/admin-session-fetch-gate";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const BACKGROUND_KEY = "cupnavi_admin_last_background_v1";
const MOBILE_RESUME_GRACE_MS = 30_000;
const UNAUTHORIZED_CONFIRMATIONS = 2;

type AuthState = "checking" | "authenticated" | "unauthenticated" | "waiting";
type Account = { id:number; email:string; role?:string|null; is_owner?:boolean };
type Cup = { id:number; name:string; role:string; public_slug?:string|null };
type SessionPayload = { account:Account; cups:Cup[] };

function clearVerifiedCache() {
  try { sessionStorage.removeItem(VERIFIED_CACHE_KEY); } catch {}
}

function writeVerifiedCache(token:string,payload:SessionPayload) {
  try {
    sessionStorage.setItem(VERIFIED_CACHE_KEY,JSON.stringify({token,account:payload.account,cups:payload.cups || [],verifiedAt:Date.now()}));
  } catch {}
}

export default function AdminAuthShell() {
  installAdminSessionFetchGate();

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
        clearVerifiedCache();
        setState("unauthenticated");
        return;
      }

      setState(current => current === "authenticated" ? current : "checking");
      try {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 9000);
        const response = await authoritativeAdminSessionFetch(`${CLIENT_API_BASE}/api/admin/session`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
          signal: controller.signal,
        });
        window.clearTimeout(timeout);

        if (response.status === 401) {
          unauthorizedRef.current += 1;
          const inResumeGrace = recentlyResumed();
          if (inResumeGrace || unauthorizedRef.current < UNAUTHORIZED_CONFIRMATIONS) {
            setState(current => current === "authenticated" ? current : "waiting");
            scheduleVerify(inResumeGrace ? 2500 : 900);
            return;
          }
          localStorage.removeItem(TOKEN_KEY);
          clearVerifiedCache();
          unauthorizedRef.current = 0;
          if (!cancelled) setState("unauthenticated");
          return;
        }

        if (!response.ok) throw new Error(`session ${response.status}`);
        const payload = await response.json() as SessionPayload;
        writeVerifiedCache(token,payload);
        unauthorizedRef.current = 0;
        try { sessionStorage.removeItem(BACKGROUND_KEY); } catch {}
        if (!cancelled) setState("authenticated");
      } catch {
        if (cancelled) return;
        unauthorizedRef.current = 0;
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
      if (!token) clearVerifiedCache();
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
    const onSessionRefresh = () => scheduleVerify(50);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("cupnavi:session-refresh",onSessionRefresh);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("cupnavi:session-refresh",onSessionRefresh);
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
      <AdminLazyExtras/>
      <AdminWorkspace key={`admin-${authKey}`} />
      <AdminOperations/>
    </>
  );
}
