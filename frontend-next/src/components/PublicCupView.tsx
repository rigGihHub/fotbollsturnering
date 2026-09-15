"use client";

import { useEffect, useMemo, useState } from "react";
import { CupSnapshot, PublicStatistics, StandingRow } from "@/lib/types";
import { getCup, getStandings, getStatistics } from "@/lib/api";
import { CupCover } from "./CupCover";
import { MatchCard } from "./MatchCard";
import { TextTvStandings } from "./TextTvStandings";
import { WeatherShareCard } from "./WeatherShareCard";

type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type Tab="matches"|"table"|"stats"|"playoff"|"info";
type MatchView="upcoming"|"results"|"all";
const matchTime=(value?:string|null)=>{const n=value?new Date(value).getTime():NaN;return Number.isFinite(n)?n:null};
const normalizeCup=(snapshot:CupSnapshot):CupSnapshot=>({
  tournament:{...(snapshot?.tournament||{}),id:Number(snapshot?.tournament?.id)||0,name:snapshot?.tournament?.name?.trim()||"Ny cup"},
  teams:Array.isArray(snapshot?.teams)?snapshot.teams:[],groups:Array.isArray(snapshot?.groups)?snapshot.groups:[],
  matches:Array.isArray(snapshot?.matches)?snapshot.matches:[],brackets:Array.isArray(snapshot?.brackets)?snapshot.brackets:[],
  venue_points:Array.isArray(snapshot?.venue_points)?snapshot.venue_points:[],participant_resolution:snapshot?.participant_resolution||{},
});

function StatisticsTable({title,metric,rows}:{title:string;metric:string;rows:Array<{player_id:number;player_name:string;team_name:string;goals:number;assists:number;yellow_cards:number;red_cards:number}>}){
  return <section className="texttv"><div className="texttv__header"><span>330</span><strong>{title}</strong><span>LIVE</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Spelare</th><th>Lag</th><th>{metric}</th></tr></thead><tbody>{rows.length?rows.map((row,index)=><tr key={`${title}-${row.player_id}`}><td>{index+1}</td><td>{row.player_name}</td><td>{row.team_name}</td><td><strong>{metric==="Mål"?row.goals:metric==="Assist"?row.assists:`${row.yellow_cards}/${row.red_cards}`}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad statistik ännu.</td></tr>}</tbody></table></div></section>;
}

function DisciplineTable({stats}:{stats:PublicStatistics}){
  return <section className="texttv"><div className="texttv__header"><span>330</span><strong>Fair play</strong><span>LAG</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Lag</th><th>Gula</th><th>Röda</th></tr></thead><tbody>{stats.discipline.length?stats.discipline.map((row,index)=><tr key={row.team_id}><td>{index+1}</td><td>{row.team_name}</td><td>{row.yellow_cards}</td><td><strong>{row.red_cards}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad disciplinstatistik ännu.</td></tr>}</tbody></table></div></section>;
}

export function PublicCupView({ publicKey, initialCup, initialStandings, reporterReturn=false }:{publicKey:string;initialCup:CupSnapshot;initialStandings:StandingsGroup[];reporterReturn?:boolean}){
  const [cup,setCup]=useState(()=>normalizeCup(initialCup)); const [standings,setStandings]=useState(Array.isArray(initialStandings)?initialStandings:[]);
  const [tab,setTab]=useState<Tab>("matches");
  const [matchView,setMatchView]=useState<MatchView>("upcoming"); const [moreOpen,setMoreOpen]=useState(false);
  const [statistics,setStatistics]=useState<PublicStatistics|null>(null); const [statisticsLoading,setStatisticsLoading]=useState(false);
  const statsEnabled=Boolean(cup.tournament.show_scorer_stats||cup.tournament.show_assist_stats||cup.tournament.show_card_stats||cup.tournament.show_fairness);
  const isMatchcamp=cup.tournament.arrangement_type==="matchcamp";
  const showTables=!isMatchcamp&&Boolean(cup.tournament.results_counted??true)&&cup.groups.length>0;
  const showPlayoffs=!isMatchcamp&&cup.brackets.length>0;

  useEffect(()=>{if(tab!=="stats"||statistics||statisticsLoading)return;let cancelled=false;setStatisticsLoading(true);getStatistics(publicKey).then(data=>{if(!cancelled)setStatistics(data)}).catch(()=>{}).finally(()=>{if(!cancelled)setStatisticsLoading(false)});return()=>{cancelled=true}},[tab,statistics,statisticsLoading,publicKey]);
  useEffect(()=>{const timer=window.setInterval(async()=>{try{const [freshCup,freshStandings]=await Promise.all([getCup(publicKey),getStandings(publicKey)]);setCup(normalizeCup(freshCup));setStandings(Array.isArray(freshStandings.groups)?freshStandings.groups:[]);if(tab==="stats"&&statsEnabled){try{setStatistics(await getStatistics(publicKey))}catch{}}}catch{}},30000);return()=>window.clearInterval(timer)},[publicKey,tab,statsEnabled]);
  useEffect(()=>{if((tab==="table"&&!showTables)||(tab==="playoff"&&!showPlayoffs))setTab("matches")},[tab,showTables,showPlayoffs]);

  const orderedMatches=useMemo(()=>[...cup.matches].sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity)),[cup.matches]);
  const upcoming=useMemo(()=>orderedMatches.filter(m=>m.home_score==null&&m.away_score==null),[orderedMatches]);
  const results=useMemo(()=>orderedMatches.filter(m=>m.home_score!=null&&m.away_score!=null).reverse(),[orderedMatches]);
  const visibleMatches=matchView==="upcoming"?upcoming:matchView==="results"?results:orderedMatches;
  const openTab=(next:Tab)=>{setTab(next);setMoreOpen(false);window.scrollTo({top:0,behavior:"smooth"});};
  const navItems:Array<[Tab,string]>=[["matches","Matcher"],...(showTables?[["table","Tabeller"] as [Tab,string]]:[]),...(statsEnabled?[["stats","Topplistor"] as [Tab,string]]:[]),...(showPlayoffs?[["playoff","Slutspel"] as [Tab,string]]:[]),["info",isMatchcamp?"Matchcampinfo":"Cupinfo"]];
  const mobileItems:Array<[Tab,string,string]>=[["matches","Matcher","▦"],...(showTables?[["table","Tabell","330"] as [Tab,string,string]]:[]),...(showPlayoffs?[["playoff","Slutspel","◆"] as [Tab,string,string]]:[])];

  return <main className="page-shell page-shell--matchday">
    {reporterReturn&&<div className="public-role-return"><span>Du granskar den publika turneringsvyn</span><a href={`/reporter?cup=${encodeURIComponent(publicKey)}`}>← Till matchrapportering</a></div>}
    <div className="public-sports-atmosphere" aria-hidden="true"><span className="sport-art sport-art--ball"/><span className="sport-art sport-art--cone"/><span className="sport-art sport-art--whistle"/><span className="sport-art sport-art--boot"/></div>
    <CupCover tournament={cup.tournament} teamCount={cup.teams.length} matchCount={cup.matches.length} groupCount={cup.groups.length}/>
    <nav className="edition-nav edition-nav--desktop" aria-label="Cupens innehåll">{navItems.map(([key,label],i)=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key)}><span>0{i+1}</span>{label}</button>)}</nav>


    {tab==="matches"&&<section><div className="section-heading"><span>MATCHPROGRAM</span><h2>Matcher</h2><p>Kommande matcher och färdiga resultat utan begränsning.</p></div><div className="match-view-filter" role="group" aria-label="Filtrera matcher"><button className={matchView==="upcoming"?"is-active":""} onClick={()=>setMatchView("upcoming")}>Kommande <b>{upcoming.length}</b></button><button className={matchView==="results"?"is-active":""} onClick={()=>setMatchView("results")}>Resultat <b>{results.length}</b></button><button className={matchView==="all"?"is-active":""} onClick={()=>setMatchView("all")}>Alla <b>{orderedMatches.length}</b></button></div>{visibleMatches.length?<div className="match-grid">{visibleMatches.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div>:<article className="empty-state"><strong>{matchView==="results"?"Inga resultat rapporterade ännu.":"Inga kommande matcher publicerade."}</strong></article>}</section>}
    {tab==="table"&&showTables&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Tabeller</h2><p>Ställningen i cupens grupper, uppdaterad med publicerade resultat.</p></div>{standings.length?<div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows}/>)}</div>:<article className="empty-state"><strong>Inga tabeller ännu</strong><p>Tabeller visas när grupper och matcher har skapats.</p></article>}</section>}
    {tab==="stats"&&statsEnabled&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Topplistor</h2><p>Registrerade matchhändelser direkt från CupNavi.</p></div>{statisticsLoading&&!statistics?<article className="empty-state"><strong>Hämtar topplistor…</strong></article>:statistics?<div className="table-stack">{statistics.enabled.scorers&&<StatisticsTable title="Målskyttar" metric="Mål" rows={statistics.scorers}/>} {statistics.enabled.assists&&<StatisticsTable title="Assistliga" metric="Assist" rows={statistics.assists}/>} {statistics.enabled.cards&&<StatisticsTable title="Spelarkort" metric="Gula/Röda" rows={statistics.cards}/>} {statistics.enabled.fairness&&<DisciplineTable stats={statistics}/>}</div>:<article className="empty-state"><strong>Topplistor kunde inte hämtas just nu.</strong></article>}</section>}

    {tab==="playoff"&&showPlayoffs&&<section><div className="section-heading"><span>SLUTSPEL</span><h2>Vägen till finalen</h2><p>Slutspelet match för match.</p></div>{cup.brackets.length?<div className="table-stack">{cup.brackets.map(bracket=><section key={bracket.id}><div className="subsection-label"><span>SLUTSPEL</span><strong>{bracket.name}</strong></div>{bracket.matches?.length?<div className="match-grid">{bracket.matches.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div>:<article className="empty-state"><strong>Matcher kommer när slutspelsträdet är publicerat.</strong></article>}</section>)}</div>:<article className="empty-state"><strong>Inget slutspel är publicerat ännu.</strong></article>}</section>}

    {tab==="info"&&<section><div className="section-heading"><span>CUPINFO</span><h2>Bra att veta</h2><p>Praktisk information för cupdagen.</p></div><div className="bracket-grid"><article className="editorial-card"><span className="feature-card__number">INFO</span><h3>{cup.tournament.organizer||"Arrangören"}</h3><p>{cup.tournament.public_information||"Arrangören har inte publicerat någon extra cupinformation ännu."}</p><div className="editorial-card__meta">{cup.tournament.arena_address||"Plats kommer"}</div></article>{cup.venue_points.map(point=><article className="feature-card" key={point.id}><span className="feature-card__number">{(point.kind||"PLATS").toUpperCase()}</span><h3>{point.label||"Cupområdet"}</h3><p>{point.detail||"Öppna platsen för mer information."}</p>{point.url&&<p><a href={point.url} target="_blank" rel="noreferrer">Öppna karta / länk →</a></p>}</article>)}<WeatherShareCard address={cup.tournament.arena_address} startDate={cup.tournament.start_date} endDate={cup.tournament.end_date} cupName={cup.tournament.name}/></div></section>}

    {moreOpen&&<div className="mobile-more-menu" role="dialog" aria-label="Fler cupvyer"><strong>Fler val</strong>{statsEnabled&&<button onClick={()=>openTab("stats")}>★ Topplistor</button>}<button onClick={()=>openTab("info")}>ⓘ Cupinfo & karta</button></div>}
    <nav className="mobile-bottom-nav" aria-label="Snabbnavigation">{mobileItems.map(([key,label,icon])=><button key={key} className={tab===key?"is-active":""} onClick={()=>openTab(key)}><span>{icon}</span>{label}</button>)}<button className={moreOpen||tab==="stats"||tab==="info"?"is-active":""} aria-expanded={moreOpen} onClick={()=>setMoreOpen(value=>!value)}><span>•••</span>Mer</button></nav>
  </main>;
}
