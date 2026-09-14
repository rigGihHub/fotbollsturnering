import { Group, Match, Team } from "@/lib/types";
import { matchStatus, participantLabel, timeLabel } from "@/lib/format";

function Kit({ color, color2, pattern }: { color?: string | null; color2?:string|null; pattern?:string|null }) {
  const c1 = color && /^#[0-9a-f]{6}$/i.test(color) ? color : "#2257d6";
  const c2 = color2 && /^#[0-9a-f]{6}$/i.test(color2) ? color2 : "#ffffff";
  const background=pattern==="Vertikala ränder"?`repeating-linear-gradient(90deg,${c1} 0 6px,${c2} 6px 12px)`
    :pattern==="Horisontella ränder"?`repeating-linear-gradient(0deg,${c1} 0 6px,${c2} 6px 12px)`
    :pattern==="Rutigt"?`conic-gradient(${c1} 25%,${c2} 0 50%,${c1} 0 75%,${c2} 0) 0 0/12px 12px`
    :pattern==="Delad"?`linear-gradient(90deg,${c1} 0 50%,${c2} 50%)`:c1;
  return <span className="kit" style={{ "--kit": c1, background } as React.CSSProperties} aria-hidden="true" />;
}

export function MatchCard({ match, teams, groups = [], index }: { match: Match; teams: Team[]; groups?:Group[]; index: number }) {
  const homeId = match.home_participant?.resolved ? match.home_participant.team_id ?? null : match.home_source?.startsWith("team:") ? Number(match.home_source.split(":")[1]) : null;
  const awayId = match.away_participant?.resolved ? match.away_participant.team_id ?? null : match.away_source?.startsWith("team:") ? Number(match.away_source.split(":")[1]) : null;
  const home = teams.find((team) => team.id === homeId);
  const away = teams.find((team) => team.id === awayId);
  const status = matchStatus(match);
  const score = match.home_score == null || match.away_score == null ? "VS" : `${match.home_score}–${match.away_score}`;
  const homeLabel=participantLabel(match.home_source,match.home_participant,teams,groups);
  const awayLabel=participantLabel(match.away_source,match.away_participant,teams,groups);
  return (
    <article className={`match-card match-card--${status}`}>
      <div className="match-card__topline">
        <span>#{String(index + 1).padStart(2, "0")}</span>
        <span>{status === "live" ? "LIVE" : status === "done" ? "SLUT" : timeLabel(match.scheduled_start)}</span>
      </div>
      <div className="match-card__body">
        <div className="team team--home"><Kit color={home?.primary_color} color2={home?.home_color_2} pattern={home?.home_pattern}/><strong>{homeLabel}</strong></div>
        <div className="score-window"><small>{match.stage || "MATCH"}</small><strong>{score}</strong></div>
        <div className="team team--away"><Kit color={away?.primary_color} color2={away?.home_color_2} pattern={away?.home_pattern}/><strong>{awayLabel}</strong></div>
      </div>
      <div className="match-card__footer"><span>PLAN {match.pitch_number || "–"}</span><span>CUPNAVI//LIVE</span></div>
    </article>
  );
}
