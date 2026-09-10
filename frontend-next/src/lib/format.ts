import { Match, Team } from "./types";

export function sourceTeamId(source?: string | null): number | null {
  if (!source?.startsWith("team:")) return null;
  const id = Number(source.split(":")[1]);
  return Number.isFinite(id) ? id : null;
}

export function teamLabel(source: string | null | undefined, teams: Team[]): string {
  const id = sourceTeamId(source);
  if (id !== null) return teams.find((team) => Number(team.id) === id)?.name || "TBD";
  return (source || "TBD").replaceAll(":", " ");
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
