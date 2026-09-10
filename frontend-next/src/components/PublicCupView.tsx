"use client";

import { useEffect, useMemo, useState } from "react";
import { CupSnapshot, PublicStatistics, StandingRow, TeamSummaryPayload } from "@/lib/types";
import { getCup, getStandings, getStatistics, getTeamSummary } from "@/lib/api";
import { timeLabel } from "@/lib/format";
import { CupCover } from "./CupCover";
import { MatchCard } from "./MatchCard";
import { TextTvStandings } from "./TextTvStandings";
import { WeatherShareCard } from "./WeatherShareCard";

type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type Tab="matchday"|"matches"|"table"|"stats"|"playoff"|"info";
const teamIdFromSource=(source?:string|null)=>source?.startsWith("team:")?Number(source.split(":")[1]):null;
const matchTime=(value?:string|null)=>{const n=value?new Date(value).getTime():NaN;return Number.isFinite(n)?n:null};

function StatisticsTable({title,metric,rows}:{title:string;metric:string;rows:Array<{player_id:number;player_name:string;team_name:string;goals:number;assists:number;yellow_cards:number;red_cards:number}>}){
  return <section className="texttv"><div className="texttv__header"><span>330</span><strong>{title}</strong><span>LIVE DATA</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Spelare</th><th>Lag</th><th>{metric}</th></tr></thead><tbody>{rows.length?rows.map((row,index)=><tr key={`${title}-${row.player_id}`}><td>{index+1}</td><td>{row.player_name}</td><td>{row.team_name}</td><td><strong>{metric==="Mål"?row.goals:metric==="Assist"?row.assists:`${row.yellow_cards}/${row.red_cards}`}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad statistik ännu.</td></tr>}</tbody></table></div></section>;
}

function DisciplineTable({stats}:{stats:PublicStatistics}){
  return <section className="texttv"><div className="texttv__header"><span>330</span><strong>Fair play</strong><span>LAG</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Lag</th><th>Gula</th><th>Röda</th></tr></thead><tbody>{stats.discipline.length?stats.discipline.map((row,index)=><tr key={row.team_id}><td>{index+1}</td><td>{row.team_name}</td><td>{row.yellow_cards}</td><td><strong>{row.red_cards}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad disciplinstatistik ännu.</td></tr>}</tbody></table></div></section>;
}

export function PublicCupView({ publicKey, initialCup, initialStandings }:{publicKey:string;initialCup:CupSnapshot;initialStandings:StandingsGroup[]}){
  const [cup,setCup]=useState(initialCup); const [standings,setStandings]=useState(initialStandings);
  const [tab,setTab]=useState<Tab>("matchday"); const [favorites,setFavorites]=useState<number[]>([]);
  const [summaries,setSummaries]=useState<Record<number,TeamSummaryPayload>>({}); const [notifyState,setNotifyState]=useState("Notiser av");
  const [shareState,setShareState]=useState("Dela cupen");
  const [statistics,setStatistics]=useState<PublicStatistics|null>(null); const [statisticsLoading,setStatisticsLoading]=useState(false);
  const statsEnabled=Boolean(cup.tournament.show_scorer_stats||cup.tournament.show_assist_stats||cup.tournament.show_card_stats||cup.tournament.show_fairness);

  useEffect(()=>{try{const raw=localStorage.getItem(`cupnavi:favorites:${publicKey}`);if(raw)setFavorites(JSON.parse(raw).filter((id:unknown)=>Number.isInteger(id)).map(Number));}catch{}},[publicKey]);
  useEffect(()=>{try{localStorage.setItem(`cupnavi:favorites:${publicKey}`,JSON.stringify(favorites));}catch{}},[favorites,publicKey]);
  useEffect(()=>{let cancelled=false;Promise.all(favorites.map(id=>getTeamSummary(publicKey,id).then(x=>[id,x] as const).catch(()=>null))).then(rows=>{if(cancelled)return;const next:Record<number,TeamSummaryPayload>={};rows.forEach(row=>{if(row)next[row[0]]=row[1]});setSummaries(next)});return()=>{cancelled=true}},[favorites,publicKey,cup]);
  useEffect(()=>{if(tab!=="stats"||statistics||statisticsLoading)return;let cancelled=false;setStatisticsLoading(true);getStatistics(publicKey).then(data=>{if(!cancelled)setStatistics(data)}).catch(()=>{}).finally(()=>{if(!cancelled)setStatisticsLoading(false)});return()=>{cancelled=true}},[tab,statistics,statisticsLoading,publicKey]);
  useEffect(()=>{const timer=window.setInterval(async()=>{try{const [freshCup,freshStandings]=await Promise.all([getCup(publicKey),getStandings(publicKey)]);setCup(freshCup);setStandings(freshStandings.groups||[]);if(tab==="stats"&&statsEnabled){try{setStatistics(await getStatistics(publicKey))}catch{}}}catch{}},30000);return()=>window.clearInterval(timer)},[publicKey,tab,statsEnabled]);

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
  const shareCup=async()=>{const url=window.location.href;try{if(navigator.share){await navigator.share({title:cup.tournament.name,text:`Följ ${cup.tournament.name} i CupNavi`,url});setShareState("Delat");return}await navigator.clipboard.writeText(url);setShareState("Länk kopierad")}catch{setShareState("Dela cupen")}};
  const navItems:Array<[Tab,string]>=[["matchday","Matchday"],["matches","Matcher"],["table","Tabeller"],...(statsEnabled?[["stats","Topplistor"] as [Tab,string]]:[]),["playoff","Slutspel"],["info","Cupinfo"]];

  return <main className="page-shell page-shell--matchday">
    <CupCover tournament={cup.tournament} teamCount={cup.teams.length}/>
    <nav className="edition-nav edition-nav--desktop" aria-label="Cupens innehåll">{navItems.map(([key,label],i)=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key)}><span>0{i+1}</span>{label}</button>)}</nav>

    {tab==="matchday"&&<section className="matchday"><div className="section-heading section-heading--compact"><span>CN//MATCHDAY</span><h2>Din cupdag</h2><p>Nästa match, rätt plan, rätt tid. Resten finns ett tryck bort.</p></div><div className="favorite-strip"><div className="favorite-strip__head"><div><strong>Mina lag</strong><span> Välj ett eller flera lag att följa.</span></div>{favorites.length>0&&<button className="favorite-clear" onClick={()=>setFavorites([])}>Rensa</button>}</div><div className="favorite-chips">{cup.teams.map(team=><button key={team.id} className={favorites.includes(team.id)?"favorite-chip is-selected":"favorite-chip"} onClick={()=>toggleFavorite(team.id)} aria-pressed={favorites.includes(team.id)}><span aria-hidden="true">{favorites.includes(team.id)?"★":"☆"}</span>{team.name}</button>)}</div></div>{heroMatch?<article className="next-match-hero"><div className="next-match-hero__label"><span>{nextFavorite?"NÄSTA FÖR DINA LAG":"NÄSTA MATCH"}</span><span>{timeLabel(heroMatch.scheduled_start)}</span></div><MatchCard match={heroMatch} teams={cup.teams} index={Math.max(0,cup.matches.findIndex(m=>m.id===heroMatch.id))}/><div className="next-match-actions">{heroPitch?.url?<a href={heroPitch.url} target="_blank" rel="noreferrer"><span aria-hidden="true">⌖</span> Hitta plan {heroMatch.pitch_number}</a>:<span><span aria-hidden="true">⌖</span> Plan {heroMatch.pitch_number||"–"}</span>}<button onClick={enableNotifications}><span className="action-symbol" aria-hidden="true">●</span>{notifyState}</button></div></article>:<article className="empty-state"><strong>Inga kommande matcher publicerade.</strong></article>}{favorites.length>0&&<><div className="subsection-label"><span>FÖLJER</span><strong>{favorites.length} lag</strong></div><div className="my-teams-grid">{favorites.map(id=>{const data=summaries[id];const team=cup.teams.find(t=>t.id===id);return <article className="team-pass" key={id}><span className="team-pass__number">FAV//{String(id).padStart(3,"0")}</span><h3>{team?.name||data?.team.name||"Lag"}</h3><div className="team-pass__facts"><span>{data?.summary.group_position?`${data.summary.group_position}:a i gruppen`:"Placering –"}</span><span>{data?`${data.summary.played}/${data.summary.matches} spelade`:"Hämtar…"}</span></div></article>})}</div></>}</section>}

    {tab==="matches"&&<section><div className="section-heading"><span>MATCHDAY CARDS</span><h2>Matcher</h2><p>Programmet som samlarkort. Resultatet får sin egen Text-TV-ruta.</p></div><div className="match-grid">{upcoming.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div></section>}
    {tab==="table"&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Tabeller</h2><p>CupNavis mörka live-lager för resultat och statistik.</p></div><div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows}/>)}</div></section>}
    {tab==="stats"&&statsEnabled&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Topplistor</h2><p>Registrerade matchhändelser direkt från CupNavi.</p></div>{statisticsLoading&&!statistics?<article className="empty-state"><strong>Hämtar topplistor…</strong></article>:statistics?<div className="table-stack">{statistics.enabled.scorers&&<StatisticsTable title="Målskyttar" metric="Mål" rows={statistics.scorers}/>} {statistics.enabled.assists&&<StatisticsTable title="Assistliga" metric="Assist" rows={statistics.assists}/>} {statistics.enabled.cards&&<StatisticsTable title="Spelarkort" metric="Gula/Röda" rows={statistics.cards}/>} {statistics.enabled.fairness&&<DisciplineTable stats={statistics}/>}</div>:<article className="empty-state"><strong>Topplistor kunde inte hämtas just nu.</strong></article>}</section>}

    {tab==="playoff"&&<section><div className="section-heading"><span>THE BRACKET ISSUE</span><h2>Slutspel</h2><p>Vägen till finalen – match för match.</p></div>{cup.brackets.length?<div className="table-stack">{cup.brackets.map(bracket=><section key={bracket.id}><div className="subsection-label"><span>BR//{String(bracket.id).padStart(2,"0")}</span><strong>{bracket.name}</strong></div>{bracket.matches?.length?<div className="match-grid">{bracket.matches.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div>:<article className="empty-state"><strong>Matcher kommer när slutspelsträdet är publicerat.</strong></article>}</section>)}</div>:<article className="empty-state"><strong>Inget slutspel är publicerat ännu.</strong></article>}</section>}

    {tab==="info"&&<section><div className="section-heading"><span>CUP GUIDE</span><h2>Cupinfo</h2><p>Det viktigaste på cupområdet samlat på samma ställe.</p></div><div className="bracket-grid"><article className="editorial-card"><span className="feature-card__number">INFO//01</span><h3>{cup.tournament.organizer||"Arrangören"}</h3><p>{cup.tournament.public_information||"Arrangören har inte publicerat någon extra cupinformation ännu."}</p><div className="editorial-card__meta">{cup.tournament.arena_address||"Plats kommer"}</div></article>{cup.venue_points.map(point=><article className="feature-card" key={point.id}><span className="feature-card__number">{(point.kind||"PLATS").toUpperCase()}</span><h3>{point.label||"Cupområdet"}</h3><p>{point.detail||"Öppna platsen för mer information."}</p>{point.url&&<p><a href={point.url} target="_blank" rel="noreferrer">Öppna karta / länk →</a></p>}</article>)}<WeatherShareCard address={cup.tournament.arena_address} startDate={cup.tournament.start_date} endDate={cup.tournament.end_date} cupName={cup.tournament.name}/><article className="feature-card"><span className="feature-card__number">SHARE//SEND</span><h3>Dela cupen</h3><p>Skicka CupNavi-länken till spelare, ledare, föräldrar och publik.</p><p><button className="favorite-chip is-selected" onClick={shareCup}>{shareState}</button></p></article></div></section>}

    <nav className="mobile-bottom-nav" aria-label="Snabbnavigation">{[["matchday","Idag"],["matches","Matcher"],["table","Tabell"],[statsEnabled?"stats":"info",statsEnabled?"Topplistor":"Info"]].map(([key,label])=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key as Tab)}><span>{key==="matchday"?"◉":key==="matches"?"▦":key==="table"?"330":key==="stats"?"★":"i"}</span>{label}</button>)}</nav>
  </main>;
}
