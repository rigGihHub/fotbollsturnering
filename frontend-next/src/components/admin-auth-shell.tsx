"use client";

import { useEffect, useRef, useState } from "react";
import AdminWorkspace from "./admin-workspace";
import AdminOperations from "./admin-operations";
import AdminStepFlow from "./admin-step-flow";
import AdminLazyExtras from "./admin-lazy-extras";
import CupCreateLauncher from "./cup-create-launcher-resilient";
import AppOpening from "./app-opening";
import { CLIENT_API_BASE } from "../lib/client-api";
import { installAdminRequestCoordinator } from "../lib/admin-request-coordinator";
import {
  authoritativeAdminSessionFetch,
  installAdminSessionFetchGate,
} from "../lib/admin-session-fetch-gate";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const VERIFIED_PERSISTENT_CACHE_KEY = "cupnavi_admin_verified_persistent_v1";
const BACKGROUND_KEY = "cupnavi_admin_last_background_v1";
const MOBILE_RESUME_GRACE_MS = 30_000;
const UNAUTHORIZED_CONFIRMATIONS = 2;

type AuthState = "checking" | "authenticated" | "unauthenticated" | "waiting";
type Account = { id:number; email:string; role?:string|null; is_owner?:boolean };
type Cup = { id:number; name:string; role:string; public_slug?:string|null };
type SessionPayload = { account:Account; cups:Cup[] };

function clearVerifiedCache() {
  try { sessionStorage.removeItem(VERIFIED_CACHE_KEY); } catch {}
  try { localStorage.removeItem(VERIFIED_PERSISTENT_CACHE_KEY); } catch {}
}

function writeVerifiedCache(token:string,payload:SessionPayload) {
  const cache = JSON.stringify({token,account:payload.account,cups:payload.cups || [],verifiedAt:Date.now()});
  try {
    sessionStorage.setItem(VERIFIED_CACHE_KEY,cache);
  } catch {}
  try {
    localStorage.setItem(VERIFIED_PERSISTENT_CACHE_KEY,cache);
  } catch {}
}

function readVerifiedCache(token:string): (SessionPayload & { token:string }) | null {
  for (const storage of [sessionStorage, localStorage]) {
    try {
      const key = storage === sessionStorage ? VERIFIED_CACHE_KEY : VERIFIED_PERSISTENT_CACHE_KEY;
      const cached = JSON.parse(storage.getItem(key) || "null");
      if (cached?.token !== token || !cached.account || !Array.isArray(cached.cups)) continue;
      return { account:cached.account, cups:cached.cups, token };
    } catch {}
  }
  return null;
}

export default function AdminAuthShell() {
  installAdminRequestCoordinator();
  installAdminSessionFetchGate();

  const [state, setState] = useState<AuthState>("checking");
  const [authKey, setAuthKey] = useState(0);
  const [verifiedSession, setVerifiedSession] = useState<(SessionPayload & { token:string }) | null>(null);
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
        setVerifiedSession(null);
        setState("unauthenticated");
        return;
      }

      const cachedSession = readVerifiedCache(token);
      if (cachedSession) {
        setVerifiedSession(cachedSession);
        setState("authenticated");
      } else {
        setState(current => current === "authenticated" || current === "waiting" ? current : "checking");
      }
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
            const stillCached = readVerifiedCache(token);
            if (stillCached) {
              setVerifiedSession(stillCached);
              setState("authenticated");
            } else {
              setState(current => current === "authenticated" ? current : "waiting");
            }
            scheduleVerify(inResumeGrace ? 2500 : 900);
            return;
          }
          localStorage.removeItem(TOKEN_KEY);
          clearVerifiedCache();
          setVerifiedSession(null);
          unauthorizedRef.current = 0;
          if (!cancelled) setState("unauthenticated");
          return;
        }

        if (!response.ok) throw new Error(`session ${response.status}`);
        const payload = await response.json() as SessionPayload;
        writeVerifiedCache(token,payload);
        setVerifiedSession({ ...payload, token });
        unauthorizedRef.current = 0;
        try { sessionStorage.removeItem(BACKGROUND_KEY); } catch {}
        if (!cancelled) setState("authenticated");
      } catch {
        if (cancelled) return;
        unauthorizedRef.current = 0;
        const stillCached = readVerifiedCache(token);
        if (stillCached) {
          setVerifiedSession(stillCached);
          setState("authenticated");
        } else {
          setState(current => current === "authenticated" ? current : "waiting");
        }
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
    return <AppOpening waiting={state === "waiting"} />;
  }

  if (state === "unauthenticated") {
    return <AdminWorkspace key={`login-${authKey}`} />;
  }

  return (
    <>
      <CupCreateLauncher/>
      <AdminStepFlow/>
      <AdminLazyExtras/>
      <AdminWorkspace key={`admin-${authKey}`} verifiedSession={verifiedSession}>
        <AdminOperations/>
      </AdminWorkspace>
    </>
  );
}
