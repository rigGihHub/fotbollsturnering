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
type MatchView="upcoming"|"results"|"all";
const teamIdFromSource=(source?:string|null)=>source?.startsWith("team:")?Number(source.split(":")[1]):null;
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

export function PublicCupView({ publicKey, initialCup, initialStandings }:{publicKey:string;initialCup:CupSnapshot;initialStandings:StandingsGroup[]}){
  const [cup,setCup]=useState(()=>normalizeCup(initialCup)); const [standings,setStandings]=useState(Array.isArray(initialStandings)?initialStandings:[]);
  const [tab,setTab]=useState<Tab>("matchday"); const [favorites,setFavorites]=useState<number[]>([]);
  const [matchView,setMatchView]=useState<MatchView>("upcoming"); const [moreOpen,setMoreOpen]=useState(false);
  const [summaries,setSummaries]=useState<Record<number,TeamSummaryPayload>>({}); const [notifyState,setNotifyState]=useState("Notiser av");
  const [shareState,setShareState]=useState("Dela cupen");
  const [statistics,setStatistics]=useState<PublicStatistics|null>(null); const [statisticsLoading,setStatisticsLoading]=useState(false);
  const statsEnabled=Boolean(cup.tournament.show_scorer_stats||cup.tournament.show_assist_stats||cup.tournament.show_card_stats||cup.tournament.show_fairness);
  const isMatchcamp=cup.tournament.arrangement_type==="matchcamp";
  const showTables=!isMatchcamp&&Boolean(cup.tournament.results_counted??true)&&cup.groups.length>0;
  const showPlayoffs=!isMatchcamp&&cup.brackets.length>0;

  useEffect(()=>{try{const raw=localStorage.getItem(`cupnavi:favorites:${publicKey}`);if(raw)setFavorites(JSON.parse(raw).filter((id:unknown)=>Number.isInteger(id)).map(Number));}catch{}},[publicKey]);
  useEffect(()=>{try{localStorage.setItem(`cupnavi:favorites:${publicKey}`,JSON.stringify(favorites));}catch{}},[favorites,publicKey]);
  useEffect(()=>{let cancelled=false;Promise.all(favorites.map(id=>getTeamSummary(publicKey,id).then(x=>[id,x] as const).catch(()=>null))).then(rows=>{if(cancelled)return;const next:Record<number,TeamSummaryPayload>={};rows.forEach(row=>{if(row)next[row[0]]=row[1]});setSummaries(next)});return()=>{cancelled=true}},[favorites,publicKey,cup]);
  useEffect(()=>{if(tab!=="stats"||statistics||statisticsLoading)return;let cancelled=false;setStatisticsLoading(true);getStatistics(publicKey).then(data=>{if(!cancelled)setStatistics(data)}).catch(()=>{}).finally(()=>{if(!cancelled)setStatisticsLoading(false)});return()=>{cancelled=true}},[tab,statistics,statisticsLoading,publicKey]);
  useEffect(()=>{const timer=window.setInterval(async()=>{try{const [freshCup,freshStandings]=await Promise.all([getCup(publicKey),getStandings(publicKey)]);setCup(normalizeCup(freshCup));setStandings(Array.isArray(freshStandings.groups)?freshStandings.groups:[]);if(tab==="stats"&&statsEnabled){try{setStatistics(await getStatistics(publicKey))}catch{}}}catch{}},30000);return()=>window.clearInterval(timer)},[publicKey,tab,statsEnabled]);
  useEffect(()=>{if((tab==="table"&&!showTables)||(tab==="playoff"&&!showPlayoffs))setTab("matchday")},[tab,showTables,showPlayoffs]);

  const orderedMatches=useMemo(()=>[...cup.matches].sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity)),[cup.matches]);
  const upcoming=useMemo(()=>orderedMatches.filter(m=>m.home_score==null&&m.away_score==null),[orderedMatches]);
  const results=useMemo(()=>orderedMatches.filter(m=>m.home_score!=null&&m.away_score!=null).reverse(),[orderedMatches]);
  const visibleMatches=matchView==="upcoming"?upcoming:matchView==="results"?results:orderedMatches;
  const favoriteMatches=useMemo(()=>{const ids=new Set(favorites);return cup.matches.filter(m=>ids.has(teamIdFromSource(m.home_source)??-1)||ids.has(teamIdFromSource(m.away_source)??-1)).sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity));},[cup.matches,favorites]);
  const now=Date.now();
  const nextFavorite=favoriteMatches.find(m=>m.home_score==null&&m.away_score==null&&(matchTime(m.scheduled_start)??0)>=now) || favoriteMatches.find(m=>m.home_score==null&&m.away_score==null);
  const nextAny=orderedMatches.find(m=>m.home_score==null&&m.away_score==null&&(matchTime(m.scheduled_start)??0)>=now) || orderedMatches.find(m=>m.home_score==null&&m.away_score==null);
  const heroMatch=nextFavorite||nextAny;
  const hasCupContent=cup.teams.length>0||cup.matches.length>0||cup.groups.length>0;
  const heroPitch=cup.venue_points.find(p=>p.kind?.toLowerCase()==="plan"&&(p.label?.toLowerCase()===`plan ${heroMatch?.pitch_number}`.toLowerCase()||p.label?.endsWith(String(heroMatch?.pitch_number))));
  const toggleFavorite=(id:number)=>setFavorites(current=>current.includes(id)?current.filter(x=>x!==id):[...current,id]);
  const enableNotifications=async()=>{if(!("Notification" in window)){setNotifyState("Stöds inte här");return}const result=await Notification.requestPermission();setNotifyState(result==="granted"?"Notiser redo":"Notiser blockerade")};
  const shareCup=async()=>{const url=window.location.href;try{if(navigator.share){await navigator.share({title:cup.tournament.name,text:`Följ ${cup.tournament.name} i CupNavi`,url});setShareState("Delat");return}await navigator.clipboard.writeText(url);setShareState("Länk kopierad")}catch{setShareState("Dela cupen")}};
  const openTab=(next:Tab)=>{setTab(next);setMoreOpen(false);window.scrollTo({top:0,behavior:"smooth"});};
  const navItems:Array<[Tab,string]>=[["matchday","Idag"],["matches","Matcher"],...(showTables?[["table","Tabeller"] as [Tab,string]]:[]),...(statsEnabled?[["stats","Topplistor"] as [Tab,string]]:[]),...(showPlayoffs?[["playoff","Slutspel"] as [Tab,string]]:[]),["info",isMatchcamp?"Matchcampinfo":"Cupinfo"]];
  const mobileItems:Array<[Tab,string,string]>=[["matchday","Idag","◉"],["matches","Matcher","▦"],...(showTables?[["table","Tabell","330"] as [Tab,string,string]]:[]),...(showPlayoffs?[["playoff","Slutspel","◆"] as [Tab,string,string]]:[])];

  return <main className="page-shell page-shell--matchday">
    <CupCover tournament={cup.tournament} teamCount={cup.teams.length} matchCount={cup.matches.length} groupCount={cup.groups.length}/>
    <nav className="edition-nav edition-nav--desktop" aria-label="Cupens innehåll">{navItems.map(([key,label],i)=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key)}><span>0{i+1}</span>{label}</button>)}</nav>

    {tab==="matchday"&&<section className="matchday"><div className="section-heading section-heading--compact"><span>CUPDAGEN</span><h2>{hasCupContent?"Det viktigaste just nu":"Cupen förbereds"}</h2><p>{hasCupContent?"Nästa match, rätt plan och rätt tid. Resten finns ett tryck bort.":"Turneringsvyn fungerar redan. Lag, matcher och tabeller visas automatiskt när de läggs in."}</p></div>{!hasCupContent&&<article className="public-setup-state"><span>FÖRHANDSVY</span><strong>Inget cupinnehåll är inlagt ännu</strong><p>Du kan kontrollera utseendet nu och återvända hit efter varje steg i administrationen.</p><a href="/admin">Fortsätt skapa cupen →</a></article>}{cup.teams.length>0&&<div className="favorite-strip"><div className="favorite-strip__head"><div><strong>Mina lag</strong><span> Välj ett eller flera lag att följa.</span></div>{favorites.length>0&&<button className="favorite-clear" onClick={()=>setFavorites([])}>Rensa</button>}</div><div className="favorite-chips">{cup.teams.map(team=><button key={team.id} className={favorites.includes(team.id)?"favorite-chip is-selected":"favorite-chip"} onClick={()=>toggleFavorite(team.id)} aria-pressed={favorites.includes(team.id)}><span aria-hidden="true">{favorites.includes(team.id)?"★":"☆"}</span>{team.name}</button>)}</div></div>}{hasCupContent&&(heroMatch?<article className="next-match-hero"><div className="next-match-hero__label"><span>{nextFavorite?"NÄSTA FÖR DINA LAG":"NÄSTA MATCH"}</span><span>{timeLabel(heroMatch.scheduled_start)}</span></div><MatchCard match={heroMatch} teams={cup.teams} index={Math.max(0,cup.matches.findIndex(m=>m.id===heroMatch.id))}/><div className="next-match-actions">{heroPitch?.url?<a href={heroPitch.url} target="_blank" rel="noreferrer"><span aria-hidden="true">⌖</span> Hitta plan {heroMatch.pitch_number}</a>:<span><span aria-hidden="true">⌖</span> Plan {heroMatch.pitch_number||"–"}</span>}<button onClick={enableNotifications}><span className="action-symbol" aria-hidden="true">●</span>{notifyState}</button></div></article>:<article className="empty-state"><strong>Matcher är inte publicerade ännu</strong><p>Lag och cupinformation finns, men matchprogrammet återstår.</p></article>)}{favorites.length>0&&<><div className="subsection-label"><span>MINA LAG</span><strong>{favorites.length} lag</strong></div><div className="my-teams-grid">{favorites.map(id=>{const data=summaries[id];const team=cup.teams.find(t=>t.id===id);return <article className="team-pass" key={id}><span className="team-pass__number">FAV//{String(id).padStart(3,"0")}</span><h3>{team?.name||data?.team.name||"Lag"}</h3><div className="team-pass__facts"><span>{data?.summary.group_position?`${data.summary.group_position}:a i gruppen`:"Placering –"}</span><span>{data?`${data.summary.played}/${data.summary.matches} spelade`:"Hämtar…"}</span></div></article>})}</div></>}</section>}

    {tab==="matches"&&<section><div className="section-heading"><span>MATCHPROGRAM</span><h2>Matcher</h2><p>Kommande matcher och färdiga resultat utan begränsning.</p></div><div className="match-view-filter" role="group" aria-label="Filtrera matcher"><button className={matchView==="upcoming"?"is-active":""} onClick={()=>setMatchView("upcoming")}>Kommande <b>{upcoming.length}</b></button><button className={matchView==="results"?"is-active":""} onClick={()=>setMatchView("results")}>Resultat <b>{results.length}</b></button><button className={matchView==="all"?"is-active":""} onClick={()=>setMatchView("all")}>Alla <b>{orderedMatches.length}</b></button></div>{visibleMatches.length?<div className="match-grid">{visibleMatches.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div>:<article className="empty-state"><strong>{matchView==="results"?"Inga resultat rapporterade ännu.":"Inga kommande matcher publicerade."}</strong></article>}</section>}
    {tab==="table"&&showTables&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Tabeller</h2><p>Ställningen i cupens grupper, uppdaterad med publicerade resultat.</p></div>{standings.length?<div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows}/>)}</div>:<article className="empty-state"><strong>Inga tabeller ännu</strong><p>Tabeller visas när grupper och matcher har skapats.</p></article>}</section>}
    {tab==="stats"&&statsEnabled&&<section><div className="section-heading"><span>TEXT-TV 330</span><h2>Topplistor</h2><p>Registrerade matchhändelser direkt från CupNavi.</p></div>{statisticsLoading&&!statistics?<article className="empty-state"><strong>Hämtar topplistor…</strong></article>:statistics?<div className="table-stack">{statistics.enabled.scorers&&<StatisticsTable title="Målskyttar" metric="Mål" rows={statistics.scorers}/>} {statistics.enabled.assists&&<StatisticsTable title="Assistliga" metric="Assist" rows={statistics.assists}/>} {statistics.enabled.cards&&<StatisticsTable title="Spelarkort" metric="Gula/Röda" rows={statistics.cards}/>} {statistics.enabled.fairness&&<DisciplineTable stats={statistics}/>}</div>:<article className="empty-state"><strong>Topplistor kunde inte hämtas just nu.</strong></article>}</section>}

    {tab==="playoff"&&showPlayoffs&&<section><div className="section-heading"><span>SLUTSPEL</span><h2>Vägen till finalen</h2><p>Slutspelet match för match.</p></div>{cup.brackets.length?<div className="table-stack">{cup.brackets.map(bracket=><section key={bracket.id}><div className="subsection-label"><span>SLUTSPEL</span><strong>{bracket.name}</strong></div>{bracket.matches?.length?<div className="match-grid">{bracket.matches.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div>:<article className="empty-state"><strong>Matcher kommer när slutspelsträdet är publicerat.</strong></article>}</section>)}</div>:<article className="empty-state"><strong>Inget slutspel är publicerat ännu.</strong></article>}</section>}

    {tab==="info"&&<section><div className="section-heading"><span>CUPINFO</span><h2>Bra att veta</h2><p>Praktisk information för cupdagen.</p></div><div className="bracket-grid"><article className="editorial-card"><span className="feature-card__number">INFO</span><h3>{cup.tournament.organizer||"Arrangören"}</h3><p>{cup.tournament.public_information||"Arrangören har inte publicerat någon extra cupinformation ännu."}</p><div className="editorial-card__meta">{cup.tournament.arena_address||"Plats kommer"}</div></article>{cup.venue_points.map(point=><article className="feature-card" key={point.id}><span className="feature-card__number">{(point.kind||"PLATS").toUpperCase()}</span><h3>{point.label||"Cupområdet"}</h3><p>{point.detail||"Öppna platsen för mer information."}</p>{point.url&&<p><a href={point.url} target="_blank" rel="noreferrer">Öppna karta / länk →</a></p>}</article>)}<WeatherShareCard address={cup.tournament.arena_address} startDate={cup.tournament.start_date} endDate={cup.tournament.end_date} cupName={cup.tournament.name}/><article className="feature-card"><span className="feature-card__number">DELA</span><h3>Dela cupen</h3><p>Skicka CupNavi-länken till spelare, ledare, föräldrar och publik.</p><p><button className="favorite-chip is-selected" onClick={shareCup}>{shareState}</button></p></article></div></section>}

    {moreOpen&&<div className="mobile-more-menu" role="dialog" aria-label="Fler cupvyer"><strong>Fler val</strong>{statsEnabled&&<button onClick={()=>openTab("stats")}>★ Topplistor</button>}<button onClick={()=>openTab("info")}>ⓘ Cupinfo & karta</button><button onClick={()=>void shareCup()}>↗ {shareState}</button></div>}
    <nav className="mobile-bottom-nav" aria-label="Snabbnavigation">{mobileItems.map(([key,label,icon])=><button key={key} className={tab===key?"is-active":""} onClick={()=>openTab(key)}><span>{icon}</span>{label}</button>)}<button className={moreOpen||tab==="stats"||tab==="info"?"is-active":""} aria-expanded={moreOpen} onClick={()=>setMoreOpen(value=>!value)}><span>•••</span>Mer</button></nav>
  </main>;
}
