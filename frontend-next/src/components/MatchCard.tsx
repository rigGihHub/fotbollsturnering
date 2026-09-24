"use client";

import { MatchWeather } from "./MatchWeather";
import type { MatchWeather as Forecast } from "@/lib/match-weather";
import { useState } from "react";
import { Group, Match, Pitch, Team } from "@/lib/types";
import { pitchLabel } from "@/lib/pitch-label";
import { matchStatus, participantLabel, timeLabel } from "@/lib/format";
import { TeamKit } from "./TeamKit";

function Side({team,label,away=false,showKits=true,showAwayKits=true,showLogos=true}:{team?:Team;label:string;away?:boolean;showKits?:boolean;showAwayKits?:boolean;showLogos?:boolean}){
  const [logoFailed,setLogoFailed]=useState(false);
  const logoSrc=String(team?.logo_url||"").trim();
  const usableLogo=/^https:\/\//i.test(logoSrc)&&!logoSrc.includes("/api/assets/club-logos/");
  return <div className={`cn-match-team ${away?"cn-match-team--away":""}`}>
    <div className="cn-match-team__visual">
      {showLogos&&usableLogo&&!logoFailed?<img className="team-crest cn-team-crest" src={logoSrc} alt="" referrerPolicy="no-referrer" onError={()=>setLogoFailed(true)}/>:null}
      {showKits&&team&&<TeamKit primary={away&&showAwayKits?team?.secondary_color:team?.primary_color} secondary={away&&showAwayKits?team?.away_color_2:team?.home_color_2} pattern={away&&showAwayKits?team?.away_pattern:team?.home_pattern}/>}
    </div>
    <div><strong>{label}</strong></div>
  </div>;
}

export function MatchCard({match,teams,groups=[],pitches=[],index,weather,showKits=true,showAwayKits=true,showLogos=true,showGoalMinutes=false}:{match:Match;teams:Team[];groups?:Group[];pitches?:Pitch[];index:number;weather?:Forecast;showKits?:boolean;showAwayKits?:boolean;showLogos?:boolean;showGoalMinutes?:boolean}){
  const homeId=match.home_participant?.resolved?match.home_participant.team_id??null:match.home_source?.startsWith("team:")?Number(match.home_source.split(":")[1]):null;
  const awayId=match.away_participant?.resolved?match.away_participant.team_id??null:match.away_source?.startsWith("team:")?Number(match.away_source.split(":")[1]):null;
  const home=teams.find(team=>team.id===homeId); const away=teams.find(team=>team.id===awayId);
  const status=matchStatus(match);
  const score=match.home_score==null||match.away_score==null?null:`${match.home_score}–${match.away_score}`;
  const homeLabel=participantLabel(match.home_source,match.home_participant,teams,groups);
  const awayLabel=participantLabel(match.away_source,match.away_participant,teams,groups);
  const pitchNames=Object.fromEntries(pitches.map(pitch=>[String(pitch.pitch_number),pitch.name]));
  const state=status==="live"?"Live":status==="halftime"?"Paus":status==="done"?"Slut":"Kommande";
  const date=match.scheduled_start?.slice(0,10)||"Datum kommer";
  const time=timeLabel(match.scheduled_start);
  return <article className={`cn-match-card cn-match-card--${status}`}>
    <header className="cn-match-card__meta"><span className="cn-match-card__kickoff"><span>{date}</span><strong>{time}</strong></span><b>{state}</b></header>
    <div className="cn-match-card__teams">
      <Side team={home} label={homeLabel} showKits={showKits} showAwayKits={showAwayKits} showLogos={showLogos}/>
      <div className="cn-match-card__score"><strong>{score||"vs"}</strong></div>
      <Side team={away} label={awayLabel} away showKits={showKits} showAwayKits={showAwayKits} showLogos={showLogos}/>
    </div>
    <footer className="cn-match-card__pitch"><span>Match {index+1}</span><strong>{pitchLabel(match.pitch_number==null?null:Number(match.pitch_number),pitchNames)}</strong></footer>
    {showGoalMinutes&&!!match.goal_minutes?.length&&<div className="cn-match-card__goals" aria-label="Målminuter">{(["home","away"] as const).map(side=>{const minutes=match.goal_minutes?.filter(goal=>goal.side===side).map(goal=>`${goal.minute}′`)||[];return minutes.length?<span key={side}><b>{side==="home"?homeLabel:awayLabel}:</b> {minutes.join(", ")}</span>:null})}</div>}
    <MatchWeather forecast={weather}/>
  </article>;
}
