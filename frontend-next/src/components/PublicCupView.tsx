"use client";

import { useEffect, useMemo, useState } from "react";
import { CupSnapshot, StandingRow, TeamSummaryPayload } from "@/lib/types";
import { getCup, getStandings, getTeamSummary } from "@/lib/api";
import { timeLabel } from "@/lib/format";
import { CupCover } from "./CupCover";
import { MatchCard } from "./MatchCard";
import { TextTvStandings } from "./TextTvStandings";

type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type Tab="matchday"|"matches"|"table"|"playoff"|"info";
const teamIdFromSource=(source?:string|null)=>source?.startsWith("team:")?Number(source.split(":")[1]):null;
const matchTime=(value?:string|null)=>{const n=value?new Date(value).getTime():NaN;return Number.isFinite(n)?n:null};

export function PublicCupView({ publicKey, initialCup, initialStandings }:{publicKey:string;initialCup:CupSnapshot;initialStandings:StandingsGroup[]}){
  const [cup,setCup]=useState(initialCup); const [standings,setStandings]=useState(initialStandings);
  const [tab,setTab]=useState<Tab>("matchday"); const [favorites,setFavorites]=useState<number[]>([]);
  const [summaries,setSummaries]=useState<Record<number,TeamSummaryPayload>>({}); const [notifyState,setNotifyState]=useState("Notiser av");

  useEffect(()=>{try{const raw=localStorage.getItem(`cupnavi:favorites:${publicKey}`);if(raw)setFavorites(JSON.parse(raw).filter((id:unknown)=>Number.isInteger(id)).map(Number));}catch{}},[publicKey]);
  useEffect(()=>{localStorage.setItem(`cupnavi:favorites:${publicKey}`,JSON.stringify(favorites));},[favorites,publicKey]);
  useEffect(()=>{let cancelled=false;Promise.all(favorites.map(id=>getTeamSummary(publicKey,id).then(x=>[id,x] as const).catch(()=>null))).then(rows=>{if(cancelled)return;const next:Record<number,TeamSummaryPayload>={};rows.forEach(row=>{if(row)next[row[0]]=row[1]});setSummaries(next)});return()=>{cancelled=true}},[favorites,publicKey,cup]);
  useEffect(()=>{const timer=window.setInterval(async()=>{try{const [freshCup,freshStandings]=await Promise.all([getCup(publicKey),getStandings(publicKey)]);setCup(freshCup);setStandings(freshStandings.groups||[])}catch{}},30000);return()=>window.clearInterval(timer)},[publicKey]);

  const orderedMatches=useMemo(()=>[...cup.matches].sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity)),[cup.matches]);
  const upcoming=useMemo(()=>orderedMatches.slice(0,18),[orderedMatches]);
  const favoriteMatches=useMemo(()=>{const ids=new Set(favorites);return cup.matches.filter(m=>ids.has(teamIdFromSource(m.home_source)??-1)||ids.has(teamIdFromSource(m.away_source)??-1)).sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity));},[cup.matches,favorites]);
  const now=Date.now();
  const nextFavorite=favoriteMatches.find(m=>m.home_score==null&&m.away_score==null&&(matchTime(m.scheduled_start)??0)>=now) || favoriteMatches.find(m=>m.home_score==null&&m.away_score==null);
  const nextAny=orderedMatches.find(m=>m.home_score==null&&m.away_score==null&&(matchTime(m.scheduled_start)??0)>=now) || orderedMatches.find(m=>m.home_score==null&&m.away_score==null);
  const heroMatch=nextFavorite||nextAny;
  const heroPitch=cup.venue_points.find(p=>p.kind?.toLowerCase()==="plan"&&(p.label?.toLowerCase()===`plan ${heroMatch?.pitch_number}`.toLowerCase()||p.label?.endsWith(String(heroMatch?.pitch_number))));
  const toggleFavorite=(id:number)=>setFavorites(current=>current.includes(id)?current.filter(x=>x!==id):[...current,id]);
  const enableNotifications=async()=>{if(!("Notification" in window)){setNotifyState("Stöds inte här");return}const result=await Notification.requestPermission();setNotifyState(result==="granted"?"Notiser redo":"Notiser blockerade")};

  return <main className="page-shell page-shell--matchday">
    <CupCover tournament={cup.tournament} teamCount={cup.teams.length}/>
    <nav className="edition-nav edition-nav--desktop" aria-label="Cupens innehåll">{[["matchday","Matchday"],["matches","Matcher"],["table","Tabeller"],["playoff","Slutspel"],["info","Cupinfo"]].map(([key,label],i)=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key as Tab)}><span>0{i+1}</span>{label}</button>)}</nav>

    {tab==="matchday"&&<section className="matchday">
      <div className="section-heading section-heading--compact"><span>CN//MATCHDAY</span><h2>Din cupdag</h2><p>Nästa match, rätt plan, rätt tid. Resten finns ett tryck bort.</p></div>
      <div className="favorite-strip"><div className="favorite-strip__head"><div><strong>Mina lag</strong><span> Välj ett eller flera lag att följa.</span></div>{favorites.length>0&&<button className="favorite-clear" onClick={()=>setFavorites([])}>Rensa</button>}</div><div className="favorite-chips">{cup.teams.map(team=><button key={team.id} className={favorites.includes(team.id)?"favorite-chip is-selected":"favorite-chip"} onClick={()=>toggleFavorite(team.id)} aria-pressed={favorites.includes(team.id)}><span aria-hidden="true">{favorites.includes(team.id)?"★":"☆"}</span>{team.name}</button>)}</div></div>
      {heroMatch?<article className="next-match-hero"><div className="next-match-hero__label"><span>{nextFavorite?"NÄSTA FÖR DINA LAG":"NÄSTA MATCH"}</span><span>{timeLabel(heroMatch.scheduled_start)}</span></div><MatchCard match={heroMatch} teams={cup.teams} index={Math.max(0,cup.matches.findIndex(m=>m.id===heroMatch.id))}/><div className="next-match-actions">{heroPitch?.url?<a href={heroPitch.url} target="_blank" rel="noreferrer"><span aria-hidden="true">⌖</span> Hitta plan {heroMatch.pitch_number}</a>:<span><span aria-hidden="true">⌖</span> Plan {heroMatch.pitch_number||"–"}</span>}<button onClick={enableNotifications}><span className="action-symbol" aria-hidden="true">●</span>{notifyState}</button></div></article>:<article className="empty-state"><strong>Inga kommande matcher publicerade.</strong></article>}
      {favorites.length>0&&<><div className="subsection-label"><span>FÖLJER</span><strong>{favorites.length} {favorites.length===1?"lag":"lag"}</strong></div><div className="my-teams-grid">{favorites.map(id=>{const data=summaries[id];const team=cup.teams.find(t=>t.id===id);return <article className="team-pass" key={id}><span className="team-pass__number">FAV//{String(id).padStart(3,"0")}</span><h3>{team?.name||data?.team.name||"Lag"}</h3><div className="team-pass__facts"><span>{data?.summary.group_position?`${data.summary.group_position}:a i gruppen`:"Placering –"}</span><span>{data?`${data.summary.played}/${data.summary.matches} spelade`:"Hämtar…"}</span></div></article>})}</div></>}
    </section>}
    {tab==="matches"&&<section><div className="section-heading"><span>MATCHDAY CARDS</span><h2>Matcher</h2><p>Programmet som samlarkort. Resultatet får sin egen Text-TV-ruta.</p></div><div className="match-grid">{upcoming.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div></section>}
    {tab==="table"&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Tabeller</h2><p>CupNavis mörka live-lager för resultat och statistik.</p></div><div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows}/>)}</div></section>}
    {tab==="playoff"&&<section><div className="section-heading"><span>THE BRACKET ISSUE</span><h2>Slutspel</h2></div><div className="bracket-grid">{cup.brackets.map(bracket=><article className="feature-card" key={bracket.id}><span className="feature-card__number">BR//{String(bracket.id).padStart(2,"0")}</span><h3>{bracket.name}</h3><p>{bracket.matches?.length||0} publicerade matcher</p></article>)}</div></section>}
    {tab==="info"&&<section><div className="section-heading"><span>CUP GUIDE</span><h2>Cupinfo</h2></div><article className="editorial-card"><h3>{cup.tournament.organizer||"Arrangören"}</h3><p>{cup.tournament.public_information||"Ingen publik information är publicerad ännu."}</p><div className="editorial-card__meta">{cup.tournament.arena_address||"Plats kommer"}</div></article></section>}
    <nav className="mobile-bottom-nav" aria-label="Snabbnavigation">{[["matchday","Idag"],["matches","Matcher"],["table","Tabell"],["info","Info"]].map(([key,label])=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key as Tab)}><span>{key==="matchday"?"◉":key==="matches"?"▦":key==="table"?"330":"i"}</span>{label}</button>)}</nav>
  </main>;
}
