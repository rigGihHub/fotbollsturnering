import { CLIENT_API_BASE } from "./client-api";

const CUP_KEY = "cupnavi_admin_active_cup_v651";

type WindowWithCoordinator = Window & {
  __cupnaviAdminCoordinatorInstalled?: boolean;
  __cupnaviAdminCoordinatorOriginalFetch?: typeof window.fetch;
};

type Inflight = {
  controller: AbortController;
  promise: Promise<Response>;
  cupId: number | null;
};

const inflight = new Map<string, Inflight>();

function activeCupId(): number | null {
  try {
    const value = Number(localStorage.getItem(CUP_KEY));
    return Number.isFinite(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

function requestUrl(input: RequestInfo | URL): URL | null {
  try {
    if (typeof input === "string") return new URL(input, window.location.href);
    if (input instanceof URL) return input;
    return new URL(input.url, window.location.href);
  } catch {
    return null;
  }
}

function requestMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method.toUpperCase();
  if (typeof Request !== "undefined" && input instanceof Request) return input.method.toUpperCase();
  return "GET";
}

function requestCupId(url: URL): number | null {
  const match = url.pathname.match(/^\/api\/admin\/cups\/(\d+)(?:\/|$)/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function cancelStaleReads(nextCupId: number | null) {
  for (const [key, entry] of inflight) {
    if (entry.cupId !== null && nextCupId !== null && entry.cupId !== nextCupId) {
      entry.controller.abort();
      inflight.delete(key);
    }
  }
}

function cloneResponsePromise(promise: Promise<Response>) {
  return promise.then(response => response.clone());
}

export function installAdminRequestCoordinator() {
  if (typeof window === "undefined") return;
  const scoped = window as WindowWithCoordinator;
  if (scoped.__cupnaviAdminCoordinatorInstalled) return;

  const originalFetch = window.fetch.bind(window);
  scoped.__cupnaviAdminCoordinatorOriginalFetch = originalFetch;
  scoped.__cupnaviAdminCoordinatorInstalled = true;

  window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = requestUrl(input);
    if (!url) return originalFetch(input, init);

    const api = new URL(CLIENT_API_BASE);
    if (url.origin !== api.origin || !url.pathname.startsWith("/api/admin/")) {
      return originalFetch(input, init);
    }

    const method = requestMethod(input, init);
    const cupId = requestCupId(url);
    const selectedCupId = activeCupId();

    if (method === "GET" && cupId !== null && selectedCupId !== null && cupId !== selectedCupId) {
      const stale = new DOMException("Stale cup request", "AbortError");
      return Promise.reject(stale);
    }

    if (method !== "GET") {
      // Mutations should never sit behind stale background reads.
      for (const [key, entry] of inflight) {
        entry.controller.abort();
        inflight.delete(key);
      }
      return originalFetch(input, init);
    }

    if (cupId !== null) cancelStaleReads(cupId);

    const headers = new Headers(init?.headers || (typeof Request !== "undefined" && input instanceof Request ? input.headers : undefined));
    const auth = headers.get("Authorization") || "";
    const key = `${method}:${url.toString()}:${auth}`;
    const existing = inflight.get(key);
    if (existing) return cloneResponsePromise(existing.promise);

    const controller = new AbortController();
    const callerSignal = init?.signal || (typeof Request !== "undefined" && input instanceof Request ? input.signal : undefined);
    const abortFromCaller = () => controller.abort();
    if (callerSignal) {
      if (callerSignal.aborted) controller.abort();
      else callerSignal.addEventListener("abort", abortFromCaller, { once: true });
    }

    const promise = originalFetch(input, { ...init, signal: controller.signal })
      .finally(() => {
        inflight.delete(key);
        callerSignal?.removeEventListener("abort", abortFromCaller);
      });

    inflight.set(key, { controller, promise, cupId });
    return cloneResponsePromise(promise);
  }) as typeof window.fetch;
}
