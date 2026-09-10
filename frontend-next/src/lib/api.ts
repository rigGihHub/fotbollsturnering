import { CupSnapshot, StandingRow } from "./types";

const API_BASE = (process.env.CUPNAVI_API_BASE || process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000").replace(/\/$/, "");

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`CupNavi API svarade ${response.status}`);
  return response.json() as Promise<T>;
}

export function getCup(publicKey: string) {
  return apiGet<CupSnapshot>(`/api/public/cups/${encodeURIComponent(publicKey)}`);
}

export function getStandings(publicKey: string) {
  return apiGet<{groups:Array<{group:{id:number;name:string};rows:StandingRow[]}>}>(`/api/public/cups/${encodeURIComponent(publicKey)}/standings`);
}

export function getTeamSummary(publicKey: string, teamId: number) {
  return apiGet<import("./types").TeamSummaryPayload>(`/api/public/cups/${encodeURIComponent(publicKey)}/teams/${teamId}/summary`);
}
