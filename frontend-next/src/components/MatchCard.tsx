import { Group, Match, MatchParticipantResolution, Team } from "@/lib/types";
import { matchStatus, participantLabel, timeLabel } from "@/lib/format";

function Kit({ color }: { color?: string | null }) {
  const safe = color && /^#[0-9a-f]{6}$/i.test(color) ? color : "#2257d6";
  return <span className="kit" style={{ "--kit": safe } as React.CSSProperties} aria-hidden="true" />;
}

export function MatchCard({ match, teams, groups = [], resolution, index }: { match: Match; teams: Team[]; groups?:Group[]; resolution?:MatchParticipantResolution; index: number }) {
  const homeId = resolution?.home?.resolved ? resolution.home.team_id ?? null : match.home_source?.startsWith("team:") ? Number(match.home_source.split(":")[1]) : null;
  const awayId = resolution?.away?.resolved ? resolution.away.team_id ?? null : match.away_source?.startsWith("team:") ? Number(match.away_source.split(":")[1]) : null;
  const home = teams.find((team) => team.id === homeId);
  const away = teams.find((team) => team.id === awayId);
  const status = matchStatus(match);
  const score = match.home_score == null || match.away_score == null ? "VS" : `${match.home_score}–${match.away_score}`;
  const homeLabel=participantLabel(match.home_source,resolution?.home,teams,groups);
  const awayLabel=participantLabel(match.away_source,resolution?.away,teams,groups);
  return (
    <article className={`match-card match-card--${status}`}>
      <div className="match-card__topline">
        <span>#{String(index + 1).padStart(2, "0")}</span>
        <span>{status === "live" ? "LIVE" : status === "done" ? "SLUT" : timeLabel(match.scheduled_start)}</span>
      </div>
      <div className="match-card__body">
        <div className="team team--home"><Kit color={home?.primary_color}/><strong>{homeLabel}</strong></div>
        <div className="score-window"><small>{match.stage || "MATCH"}</small><strong>{score}</strong></div>
        <div className="team team--away"><Kit color={away?.primary_color}/><strong>{awayLabel}</strong></div>
      </div>
      <div className="match-card__footer"><span>PLAN {match.pitch_number || "–"}</span><span>CUPNAVI//LIVE</span></div>
    </article>
  );
}
