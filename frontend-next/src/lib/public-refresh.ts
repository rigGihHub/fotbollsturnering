export const MIN_REFRESH_BACKOFF_MS = 30_000;
export const MAX_REFRESH_BACKOFF_MS = 120_000;

// A returning visitor gets an immediate refresh from the visibility handler.
// While the page stays open, quiet cups need fewer requests than live matches.
export function nextPublicRefreshDelay(
  matches: Array<{match_status?:string|null}>,
  nextAllowedRefresh: number,
  now = Date.now(),
  recovering = false,
): number {
  const live = matches.some(match => match.match_status === "live" || match.match_status === "halftime");
  const baseDelay = recovering ? MIN_REFRESH_BACKOFF_MS : live ? 20_000 : 120_000;
  return Math.max(baseDelay, nextAllowedRefresh - now);
}

export function nextPublicRefreshBackoff(previous: number, retryAfter?: number): number {
  return Math.min(
    MAX_REFRESH_BACKOFF_MS,
    Math.max(retryAfter || 0, previous ? previous * 2 : MIN_REFRESH_BACKOFF_MS),
  );
}
