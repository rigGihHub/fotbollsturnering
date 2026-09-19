"use client";

import { useState } from "react";
import { Group, Match, Pitch, Team } from "@/lib/types";
import { pitchLabel } from "@/lib/pitch-label";
import { matchStatus, participantLabel, timeLabel } from "@/lib/format";
import { TeamKit } from "./TeamKit";

function Side({team,label,away=false,showKits=true,showLogos=true}:{team?:Team;label:string;away?:boolean;showKits?:boolean;showLogos?:boolean}){
  const [logoFailed,setLogoFailed]=useState(false);
  return <div className={`public-match-team ${away?"public-match-team--away":""}`}>
    <div className="public-match-team__visual">
      {showLogos&&team?.logo_url&&!logoFailed?<img className="team-crest" src={team.logo_url} alt="" referrerPolicy="no-referrer" onError={()=>setLogoFailed(true)}/>:null}
      {showKits&&<TeamKit primary={away?team?.secondary_color:team?.primary_color} secondary={away?team?.away_color_2:team?.home_color_2} pattern={away?team?.away_pattern:team?.home_pattern}/>}
    </div>
    <div><small>{away?"Borta":"Hemma"}</small><strong>{label}</strong></div>
  </div>;
}

export function MatchCard({match,teams,groups=[],pitches=[],index,showKits=true,showLogos=true}:{match:Match;teams:Team[];groups?:Group[];pitches?:Pitch[];index:number;showKits?:boolean;showLogos?:boolean}){
  const homeId=match.home_participant?.resolved?match.home_participant.team_id??null:match.home_source?.startsWith("team:")?Number(match.home_source.split(":")[1]):null;
  const awayId=match.away_participant?.resolved?match.away_participant.team_id??null:match.away_source?.startsWith("team:")?Number(match.away_source.split(":")[1]):null;
  const home=teams.find(team=>team.id===homeId); const away=teams.find(team=>team.id===awayId);
  const status=matchStatus(match);
  const score=match.home_score==null||match.away_score==null?null:`${match.home_score}–${match.away_score}`;
  const homeLabel=participantLabel(match.home_source,match.home_participant,teams,groups);
  const awayLabel=participantLabel(match.away_source,match.away_participant,teams,groups);
  const pitchNames=Object.fromEntries(pitches.map(pitch=>[String(pitch.pitch_number),pitch.name]));
  const state=status==="live"?"Live":status==="halftime"?"Paus":status==="done"?"Slut":timeLabel(match.scheduled_start);
  return <article className={`public-match-card public-match-card--${status}`}>
    <header className="public-match-card__meta"><span>Match {index+1}</span><b>{state}</b></header>
    <div className="public-match-card__teams">
      <Side team={home} label={homeLabel} showKits={showKits} showLogos={showLogos}/>
      <div className="public-match-card__score"><strong>{score||"vs"}</strong></div>
      <Side team={away} label={awayLabel} away showKits={showKits} showLogos={showLogos}/>
    </div>
    <footer className="public-match-card__pitch">{pitchLabel(match.pitch_number==null?null:Number(match.pitch_number),pitchNames)}</footer>
  </article>;
}
