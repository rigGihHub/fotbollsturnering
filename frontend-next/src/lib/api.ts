import { CupSnapshot, Match, PublicStatistics, StandingRow } from "./types";

const API_BASE = (process.env.CUPNAVI_API_BASE || process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000").replace(/\/$/, "");

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`CupNavi API svarade ${response.status}`);
  return response.json() as Promise<T>;
}

function hydrateMatch(match:Match,cup:CupSnapshot):Match {
  const resolved=cup.participant_resolution?.[String(match.id)];
  if (!resolved) return match;
  return {...match,home_participant:resolved.home,away_participant:resolved.away};
}

function hydrateParticipants(cup:CupSnapshot):CupSnapshot {
  return {
    ...cup,
    matches:(cup.matches||[]).map(match=>hydrateMatch(match,cup)),
    brackets:(cup.brackets||[]).map(bracket=>({...bracket,matches:(bracket.matches||[]).map(match=>hydrateMatch(match,cup))})),
  };
}

export async function getCup(publicKey: string) {
  const cup=await apiGet<CupSnapshot>(`/api/public/cups/${encodeURIComponent(publicKey)}`);
  return hydrateParticipants(cup);
}

export function getStandings(publicKey: string) {
  return apiGet<{groups:Array<{group:{id:number;name:string};rows:StandingRow[]}>}>(`/api/public/cups/${encodeURIComponent(publicKey)}/standings`);
}

export function getStatistics(publicKey: string) {
  return apiGet<PublicStatistics>(`/api/public/cups/${encodeURIComponent(publicKey)}/statistics`);
}

export function getTeamSummary(publicKey: string, teamId: number) {
  return apiGet<import("./types").TeamSummaryPayload>(`/api/public/cups/${encodeURIComponent(publicKey)}/teams/${teamId}/summary`);
}
