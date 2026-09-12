import { Group, Match, ResolvedParticipant, Team } from "./types";

export function sourceTeamId(source?: string | null): number | null {
  if (!source?.startsWith("team:")) return null;
  const id = Number(source.split(":")[1]);
  return Number.isFinite(id) ? id : null;
}

function placementLabel(value:number):string {
  if (value===1) return "1:a";
  if (value===2) return "2:a";
  if (value===3) return "3:a";
  return `${value}:a`;
}

export function sourceLabel(source:string|null|undefined, teams:Team[], groups:Group[] = []):string {
  if (!source) return "Lag ej klart";
  const parts=source.split(":");
  if (parts[0]==="team") {
    const id=Number(parts[1]);
    return teams.find(team=>Number(team.id)===id)?.name || "Lag ej klart";
  }
  if (parts[0]==="group" && parts.length>=3) {
    const groupId=Number(parts[1]);
    const placement=Number(parts[2]);
    const group=groups.find(item=>Number(item.id)===groupId);
    const groupName=group?.name || `Grupp ${groupId}`;
    return Number.isFinite(placement) ? `${placementLabel(placement)} ${groupName}` : groupName;
  }
  if (parts[0]==="winner" && Number.isFinite(Number(parts[1]))) return `Vinnare match ${parts[1]}`;
  if (parts[0]==="loser" && Number.isFinite(Number(parts[1]))) return `Förlorare match ${parts[1]}`;
  return source.replaceAll(":", " ");
}

export function participantLabel(
  source:string|null|undefined,
  resolved:ResolvedParticipant|undefined,
  teams:Team[],
  groups:Group[] = [],
):string {
  if (resolved?.resolved && resolved.team_name) return resolved.team_name;
  if (resolved?.kind==="legacy" && resolved.team_name) return resolved.team_name;
  return sourceLabel(source,teams,groups);
}

export function teamLabel(source: string | null | undefined, teams: Team[]): string {
  return sourceLabel(source,teams);
}

export function timeLabel(value?: string | null): string {
  if (!value) return "Tid kommer";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("sv-SE", { hour: "2-digit", minute: "2-digit" }).format(date);
}

export function dateLabel(value?: string | null): string {
  if (!value) return "Datum kommer";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("sv-SE", { day: "numeric", month: "long", year: "numeric" }).format(date);
}

export function matchStatus(match: Match): "live" | "done" | "next" {
  if (match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined) return "done";
  if (match.scheduled_start) {
    const start = new Date(match.scheduled_start).getTime();
    const now = Date.now();
    if (Number.isFinite(start) && start <= now && now <= start + 90 * 60 * 1000) return "live";
  }
  return "next";
}
