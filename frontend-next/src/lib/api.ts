import { CupSnapshot, Match, PublicStatistics, StandingRow } from "./types";

const API_BASE = (process.env.CUPNAVI_API_BASE || process.env.NEXT_PUBLIC_CUPNAVI_API_BASE || "http://localhost:8000").replace(/\/$/, "");

export class CupNaviApiError extends Error {
  constructor(public readonly status:number, message:string, public readonly retryAfterMs?:number){super(message);this.name="CupNaviApiError";}
}

const RETRY_DELAYS_MS=[300];
const REQUEST_TIMEOUT_MS=6500;

function retryAfterMs(response:Response):number|undefined {
  const header=response.headers.get("retry-after");
  if(!header)return undefined;
  const seconds=Number(header);
  if(Number.isFinite(seconds)&&seconds>0)return Math.min(seconds*1000,120000);
  const retryAt=Date.parse(header);
  if(Number.isFinite(retryAt))return Math.max(0,Math.min(retryAt-Date.now(),120000));
  return undefined;
}

async function apiGet<T>(path: string): Promise<T> {
  let lastError:unknown;
  for(let attempt=0;attempt<=RETRY_DELAYS_MS.length;attempt+=1){
    try{
      const separator=path.includes("?")?"&":"?";
      const response = await fetch(`${API_BASE}${path}${separator}_cn_attempt=${attempt}`,{ cache: "no-store", signal:AbortSignal.timeout(REQUEST_TIMEOUT_MS) });
      if(response.ok)return response.json() as Promise<T>;
      const error=new CupNaviApiError(response.status,`CupNavi API svarade ${response.status}`,retryAfterMs(response));
      if(response.status<500||attempt===RETRY_DELAYS_MS.length)throw error;
      lastError=error;
    }catch(error){
      if(error instanceof CupNaviApiError&&error.status<500)throw error;
      lastError=error;
      if(attempt===RETRY_DELAYS_MS.length)throw error;
    }
    await new Promise(resolve=>setTimeout(resolve,RETRY_DELAYS_MS[attempt]));
  }
  throw lastError;
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
