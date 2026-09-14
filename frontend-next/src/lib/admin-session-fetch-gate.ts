import { CLIENT_API_BASE } from "./client-api";

const TOKEN_KEY = "cupnavi_admin_session_v629";
const VERIFIED_CACHE_KEY = "cupnavi_admin_verified_v1";
const AUTHORITATIVE_HEADER = "X-CupNavi-Auth-Probe";
const AUTHORITATIVE_VALUE = "authoritative";

type VerifiedCache = {
  token?: string;
  account?: unknown;
  cups?: unknown[];
  verifiedAt?: number;
};

type WindowWithGate = Window & {
  __cupnaviSessionFetchGateInstalled?: boolean;
  __cupnaviOriginalFetch?: typeof window.fetch;
};

function cachedSessionFor(token:string):VerifiedCache|null {
  try {
    const raw = sessionStorage.getItem(VERIFIED_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as VerifiedCache;
    if (parsed.token !== token || !parsed.account || !Array.isArray(parsed.cups)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function sessionResponse(cache:VerifiedCache):Response {
  return new Response(JSON.stringify({ account:cache.account, cups:cache.cups || [] }), {
    status:200,
    headers:{"Content-Type":"application/json","X-CupNavi-Session-Source":"verified-cache"},
  });
}

function requestUrl(input:RequestInfo | URL):string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function requestMethod(input:RequestInfo | URL, init?:RequestInit):string {
  if (init?.method) return init.method.toUpperCase();
  if (typeof Request !== "undefined" && input instanceof Request) return input.method.toUpperCase();
  return "GET";
}

function requestHeaders(input:RequestInfo | URL, init?:RequestInit):Headers {
  if (init?.headers) return new Headers(init.headers);
  if (typeof Request !== "undefined" && input instanceof Request) return new Headers(input.headers);
  return new Headers();
}

export function installAdminSessionFetchGate() {
  if (typeof window === "undefined") return;
  const scoped = window as WindowWithGate;
  if (scoped.__cupnaviSessionFetchGateInstalled) return;

  const originalFetch = window.fetch.bind(window);
  scoped.__cupnaviOriginalFetch = originalFetch;
  scoped.__cupnaviSessionFetchGateInstalled = true;

  window.fetch = (async (input:RequestInfo | URL, init?:RequestInit) => {
    const method = requestMethod(input,init);
    if (method !== "GET") return originalFetch(input,init);

    let url:URL;
    try { url = new URL(requestUrl(input),window.location.href); }
    catch { return originalFetch(input,init); }

    const sessionUrl = new URL(`${CLIENT_API_BASE}/api/admin/session`);
    if (url.origin !== sessionUrl.origin || url.pathname !== sessionUrl.pathname) return originalFetch(input,init);

    const headers = requestHeaders(input,init);
    if (headers.get(AUTHORITATIVE_HEADER) === AUTHORITATIVE_VALUE) return originalFetch(input,init);

    const auth = headers.get("Authorization") || "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : localStorage.getItem(TOKEN_KEY) || "";
    if (!token) return originalFetch(input,init);

    const cached = cachedSessionFor(token);
    if (cached) return sessionResponse(cached);

    return originalFetch(input,init);
  }) as typeof window.fetch;
}

export const ADMIN_SESSION_AUTHORITATIVE_HEADER = AUTHORITATIVE_HEADER;
export const ADMIN_SESSION_AUTHORITATIVE_VALUE = AUTHORITATIVE_VALUE;
