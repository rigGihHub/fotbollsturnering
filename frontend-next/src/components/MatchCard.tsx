import { Group, Match, Team } from "@/lib/types";
import { matchStatus, participantLabel, timeLabel } from "@/lib/format";
import { TeamKit } from "./TeamKit";

function TeamIdentity({team,label,side}:{team?:Team;label:string;side:"home"|"away"}){
  const isAway=side==="away";
  return <div className={`team team--${side}`}>
    <span className="team-visual">
      {team?.logo_url?<img className="team-crest" src={team.logo_url} alt="" referrerPolicy="no-referrer"/>:null}
      <TeamKit
        primary={isAway?team?.secondary_color:team?.primary_color}
        secondary={isAway?team?.away_color_2:team?.home_color_2}
        pattern={isAway?team?.away_pattern:team?.home_pattern}
      />
    </span>
    <span className="team-copy"><small>{isAway?"BORTA":"HEMMA"}</small><strong>{label}</strong></span>
  </div>;
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
        <TeamIdentity team={home} label={homeLabel} side="home"/>
        <div className="score-window"><small>{match.stage || "MATCH"}</small><strong>{score}</strong></div>
        <TeamIdentity team={away} label={awayLabel} side="away"/>
      </div>
      <div className="match-card__footer"><span>PLAN {match.pitch_number || "–"}</span><span>CUPNAVI//LIVE</span></div>
    </article>
  );
}
