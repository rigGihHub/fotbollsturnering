"use client";

import { useMatchWeather } from "@/lib/use-match-weather";
import { PlacementTables } from "./PlacementTables";

import { useEffect, useMemo, useRef, useState } from "react";
import { CupSnapshot, PublicStatistics, StandingRow } from "@/lib/types";
import { CupNaviApiError, getCup, getStandings, getStatistics } from "@/lib/api";
import { CupCover } from "./CupCover";
import { MatchCard } from "./MatchCard";
import { TextTvStandings } from "./TextTvStandings";
import { WeatherShareCard } from "./WeatherShareCard";
import { matchStatus } from "@/lib/format";

type StandingsGroup={group:{id:number;name:string};rows:StandingRow[]};
type Tab="matches"|"table"|"stats"|"playoff"|"info";
type MatchView="upcoming"|"results"|"all";
const MIN_REFRESH_BACKOFF_MS=30000;
const MAX_REFRESH_BACKOFF_MS=120000;
const matchTime=(value?:string|null)=>{const n=value?new Date(value).getTime():NaN;return Number.isFinite(n)?n:null};
const normalizeCup=(snapshot:CupSnapshot):CupSnapshot=>({
  tournament:{...(snapshot?.tournament||{}),id:Number(snapshot?.tournament?.id)||0,name:snapshot?.tournament?.name?.trim()||"Ny cup"},
  placement_groups:Array.isArray(snapshot?.placement_groups)?snapshot.placement_groups:[],
  teams:Array.isArray(snapshot?.teams)?snapshot.teams:[],groups:Array.isArray(snapshot?.groups)?snapshot.groups:[],
  matches:Array.isArray(snapshot?.matches)?snapshot.matches:[],brackets:Array.isArray(snapshot?.brackets)?snapshot.brackets:[],
  pitches:Array.isArray(snapshot?.pitches)?snapshot.pitches:[],venue_points:Array.isArray(snapshot?.venue_points)?snapshot.venue_points:[],participant_resolution:snapshot?.participant_resolution||{},
});
const formatDateTime=(value?:string|null)=>value?value.replace("T"," ").slice(0,16):null;
const formatDateRange=(start?:string|null,end?:string|null)=>start&&end&&end!==start?`${start} - ${end}`:start||"Datum kommer";

function StatisticsTable({title,metric,rows}:{title:string;metric:string;rows:Array<{player_id:number;player_name:string;team_name:string;goals:number;assists:number;yellow_cards:number;red_cards:number}>}){
  return <section className="texttv"><div className="texttv__header"><span>STATISTIK</span><strong>{title}</strong><span>LIVE</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Spelare</th><th>Lag</th><th>{metric}</th></tr></thead><tbody>{rows.length?rows.map((row,index)=><tr key={`${title}-${row.player_id}`}><td>{index+1}</td><td>{row.player_name}</td><td>{row.team_name}</td><td><strong>{metric==="Mål"?row.goals:metric==="Assist"?row.assists:`${row.yellow_cards}/${row.red_cards}`}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad statistik ännu.</td></tr>}</tbody></table></div></section>;
}

function DisciplineTable({stats}:{stats:PublicStatistics}){
  return <section className="texttv"><div className="texttv__header"><span>STATISTIK</span><strong>Fair play</strong><span>LAG</span></div><div className="texttv__scroll"><table><thead><tr><th>#</th><th>Lag</th><th>Gula</th><th>Röda</th></tr></thead><tbody>{stats.discipline.length?stats.discipline.map((row,index)=><tr key={row.team_id}><td>{index+1}</td><td>{row.team_name}</td><td>{row.yellow_cards}</td><td><strong>{row.red_cards}</strong></td></tr>):<tr><td colSpan={4}>Ingen registrerad disciplinstatistik ännu.</td></tr>}</tbody></table></div></section>;
}

export function PublicCupView({ publicKey, initialCup, initialStandings, reporterReturn=false }:{publicKey:string;initialCup:CupSnapshot;initialStandings:StandingsGroup[];reporterReturn?:boolean}){
  const [cup,setCup]=useState(()=>normalizeCup(initialCup)); const cupRef=useRef(cup); const [standings,setStandings]=useState(Array.isArray(initialStandings)?initialStandings:[]);
  const nextAllowedRefreshRef=useRef(0); const publicRefreshBackoffMs=useRef(0);
  const [standingsLoaded,setStandingsLoaded]=useState(initialStandings.length>0); const [standingsLoading,setStandingsLoading]=useState(false); const standingsRequestRef=useRef(false);
  const [tab,setTab]=useState<Tab>("matches");
  const [matchView,setMatchView]=useState<MatchView>("all"); const [moreOpen,setMoreOpen]=useState(false);
  const [visibleCount,setVisibleCount]=useState(18); const loadMoreRef=useRef<HTMLDivElement|null>(null);
  const [unavailable,setUnavailable]=useState(false); const [refreshProblem,setRefreshProblem]=useState(false);
  const [statistics,setStatistics]=useState<PublicStatistics|null>(null); const [statisticsLoading,setStatisticsLoading]=useState(false);
  const statsEnabled=Boolean(cup.tournament.show_scorer_stats||cup.tournament.show_assist_stats||cup.tournament.show_card_stats||cup.tournament.show_fairness);
  const isMatchcamp=cup.tournament.arrangement_type==="matchcamp";
  const showTables=!isMatchcamp&&Boolean(cup.tournament.results_counted??true)&&cup.groups.length>0;
  const showPlayoffs=!isMatchcamp&&cup.brackets.length>0;
  const playoffDestinations=useMemo(()=>cup.brackets.map(bracket=>String(bracket.name||"").trim()).filter(Boolean),[cup.brackets]);
  const playoffPositionMap=useMemo(()=>{
    const map:Record<number,number>={};
    cup.brackets.forEach((bracket,bracketIndex)=>{
      const raw=[bracket.qualifying_positions,bracket.group_positions,bracket.qualification_rule,bracket.source_rule].find(value=>typeof value==="string"&&value.trim());
      if(!raw)return;
      const text=String(raw);
      const nums=new Set<number>();
      for(const match of text.matchAll(/(\d+)\s*[-–]\s*(\d+)/g)){
        const start=Number(match[1]),end=Number(match[2]);
        if(start>0&&end>=start&&end-start<=16)for(let position=start;position<=end;position++)nums.add(position);
      }
      for(const match of text.matchAll(/\b(?:plats(?:ering)?|placering|position|plats)?\s*(\d+)\b/gi))if(Number(match[1])>0)nums.add(Number(match[1]));
      nums.forEach(position=>{if(map[position]===undefined)map[position]=bracketIndex;});
    });
    return map;
  },[cup.brackets]);
  const showPublicKits=cup.tournament.show_public_kits!==false&&cup.tournament.show_public_kits!==0;
  const showPublicAwayKits=cup.tournament.show_public_away_kits!==false&&cup.tournament.show_public_away_kits!==0;
  const showPublicLogos=cup.tournament.show_public_logos!==false&&cup.tournament.show_public_logos!==0;
  const weatherConfigured=cup.tournament.show_public_weather_configured===true||cup.tournament.show_public_weather_configured===1;
  const showPublicWeather=!weatherConfigured||Boolean(cup.tournament.show_public_weather);
  const matchWeather=useMatchWeather(showPublicWeather&&(tab==="matches"||tab==="playoff"),[...cup.matches,...cup.brackets.flatMap(b=>b.matches||[])],cup.pitches||[],cup.tournament.arena_address);
  const matchHalves=Number(cup.tournament.halves||0)>0?Number(cup.tournament.halves):2;
  const matchMinutesPerHalf=Number(cup.tournament.minutes_per_half||0)>0?Number(cup.tournament.minutes_per_half):20;
  const halftimeMinutes=Number(cup.tournament.halftime_minutes||0);
  const hasMatchDuration=matchMinutesPerHalf>0;

  useEffect(()=>{cupRef.current=cup},[cup]);
  useEffect(()=>{if(tab!=="stats"||statistics||statisticsLoading)return;let cancelled=false;setStatisticsLoading(true);getStatistics(publicKey).then(data=>{if(!cancelled)setStatistics(data)}).catch(()=>{}).finally(()=>{if(!cancelled)setStatisticsLoading(false)});return()=>{cancelled=true}},[tab,statistics,statisticsLoading,publicKey]);
  useEffect(()=>{if(tab!=="table"||!showTables||standingsLoaded||standingsRequestRef.current)return;let cancelled=false;standingsRequestRef.current=true;setStandingsLoading(true);getStandings(publicKey).then(data=>{if(!cancelled){setStandings(Array.isArray(data.groups)?data.groups:[]);setStandingsLoaded(true)}}).catch(()=>{if(!cancelled)setStandingsLoaded(true)}).finally(()=>{standingsRequestRef.current=false;if(!cancelled)setStandingsLoading(false)});return()=>{cancelled=true}},[publicKey,showTables,standingsLoaded,tab]);
  useEffect(()=>{let busy=false;const refresh=async()=>{if(busy||document.visibilityState!=="visible"||Date.now()<nextAllowedRefreshRef.current)return;busy=true;try{const freshCup=await getCup(publicKey);publicRefreshBackoffMs.current=0;nextAllowedRefreshRef.current=0;setUnavailable(false);setRefreshProblem(false);setCup(normalizeCup(freshCup));if(tab==="table"&&showTables){try{const freshStandings=await getStandings(publicKey);setStandings(Array.isArray(freshStandings.groups)?freshStandings.groups:[]);setStandingsLoaded(true)}catch{}}if(tab==="stats"&&statsEnabled){try{setStatistics(await getStatistics(publicKey))}catch{}}}catch(error){if(error instanceof CupNaviApiError&&error.status===404){setUnavailable(true);publicRefreshBackoffMs.current=0;nextAllowedRefreshRef.current=0}else{const retryAfter=error instanceof CupNaviApiError?error.retryAfterMs:undefined;publicRefreshBackoffMs.current=Math.min(MAX_REFRESH_BACKOFF_MS,Math.max(retryAfter||0,publicRefreshBackoffMs.current?publicRefreshBackoffMs.current*2:MIN_REFRESH_BACKOFF_MS));nextAllowedRefreshRef.current=Date.now()+publicRefreshBackoffMs.current;setRefreshProblem(true)}}finally{busy=false}};const nextDelay=()=>{const baseDelay=cupRef.current.matches.some(match=>["live","halftime"].includes(match.match_status||""))?10000:30000;const cooldownMs=Math.max(0,nextAllowedRefreshRef.current-Date.now());return cooldownMs?Math.max(cooldownMs,baseDelay):baseDelay};let timer=window.setTimeout(function tick(){void refresh().finally(()=>{timer=window.setTimeout(tick,nextDelay())})},nextDelay());const onVisibility=()=>{if(document.visibilityState==="visible")void refresh()};document.addEventListener("visibilitychange",onVisibility);return()=>{window.clearTimeout(timer);document.removeEventListener("visibilitychange",onVisibility)}},[publicKey,showTables,tab,statsEnabled]);
  useEffect(()=>{if((tab==="table"&&!showTables)||(tab==="playoff"&&!showPlayoffs))setTab("matches")},[tab,showTables,showPlayoffs]);

  const orderedMatches=useMemo(()=>[...cup.matches].sort((a,b)=>(matchTime(a.scheduled_start)??Infinity)-(matchTime(b.scheduled_start)??Infinity)),[cup.matches]);
  const firstScheduledMatch=orderedMatches.find(match=>match.scheduled_start);
  const scheduledPitchCount=(cup.pitches||[]).length;
  const practicalPoints=cup.venue_points.filter(point=>point.label||point.detail||point.url);
  const visitorInfoText=String(cup.tournament.public_information||"").trim();
  const upcoming=useMemo(()=>orderedMatches.filter(m=>matchStatus(m)!=="done"),[orderedMatches]);
  const results=useMemo(()=>orderedMatches.filter(m=>matchStatus(m)==="done").reverse(),[orderedMatches]);
  const filteredMatches=matchView==="upcoming"?upcoming:matchView==="results"?results:orderedMatches;
  const visibleMatches=filteredMatches.slice(0,visibleCount);
  useEffect(()=>{setVisibleCount(18)},[matchView]);
  useEffect(()=>{const node=loadMoreRef.current;if(!node||visibleCount>=filteredMatches.length)return;const observer=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting))setVisibleCount(count=>Math.min(count+18,filteredMatches.length))},{rootMargin:"500px"});observer.observe(node);return()=>observer.disconnect()},[filteredMatches.length,visibleCount]);
  const matchNumberById=useMemo(()=>new Map(orderedMatches.map((match,index)=>[match.id,index])),[orderedMatches]);
  const openTab=(next:Tab)=>{setTab(next);setMoreOpen(false);window.scrollTo({top:0,behavior:"smooth"});};
  const placementGroups=cup.placement_groups||[];
  const hasPlacementGroups=placementGroups.length>0;
  const navItems:Array<[Tab,string]>=[["matches","Matcher"],...(showTables?[["table","Tabeller"] as [Tab,string]]:[]),...(statsEnabled?[["stats","Topplistor"] as [Tab,string]]:[]),...(showPlayoffs?[["playoff","Slutspel"] as [Tab,string]]:[]),["info",isMatchcamp?"Matchcampinfo":"Cupinfo"]];
  const mobileItems:Array<[Tab,string,string]>=[["matches","Matcher","▦"],...(showTables?[["table","Tabeller","▤"] as [Tab,string,string]]:[]),...(showPlayoffs?[["playoff","Slutspel","◆"] as [Tab,string,string]]:[])];

  if(unavailable)return <main className="page-shell page-shell--matchday"><article className="empty-state"><strong>Cupen är inte längre publicerad.</strong><p>Den kan ha flyttats till papperskorgen eller fått en ny publik adress.</p><a href="/">Till CupNavi</a></article></main>;

  return <main className="page-shell page-shell--matchday page-shell--public-v3">
    {reporterReturn&&<div className="public-role-return"><span>Du granskar den publika turneringsvyn</span><a href={`/reporter?cup=${encodeURIComponent(publicKey)}`}>← Till matchrapportering</a></div>}
    <CupCover tournament={cup.tournament} teamCount={cup.teams.length} matchCount={cup.matches.length} groupCount={cup.groups.length}/>
    <nav className="edition-nav edition-nav--desktop" aria-label="Cupens innehåll">{navItems.map(([key,label])=><button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key)}>{label}</button>)}</nav>


    {tab==="matches"&&<section className="public-matches-v3"><div className="public-section-head"><div><span>Matchprogram</span><h2>Matcher</h2></div><p>Kommande matcher och resultat</p></div><div className={`public-live-status${refreshProblem?" is-stale":""}`}><span className="public-live-status__dot"/>{refreshProblem?"Anslutningen svajar · visar senast hämtade data":"Live · uppdateras automatiskt"}</div><div className="match-view-filter" role="group" aria-label="Filtrera matcher"><button className={matchView==="all"?"is-active":""} onClick={()=>setMatchView("all")}>Alla <b>{orderedMatches.length}</b></button><button className={matchView==="upcoming"?"is-active":""} onClick={()=>setMatchView("upcoming")}>Kommande <b>{upcoming.length}</b></button><button className={matchView==="results"?"is-active":""} onClick={()=>setMatchView("results")}>Resultat <b>{results.length}</b></button></div>{visibleMatches.length?<><div className="match-grid">{visibleMatches.map(match=><MatchCard key={match.id} weather={matchWeather(match)} match={match} teams={cup.teams} groups={cup.groups} pitches={cup.pitches||[]} index={matchNumberById.get(match.id)??0} showKits={showPublicKits} showAwayKits={showPublicAwayKits} showLogos={showPublicLogos}/>)}</div>{visibleCount<filteredMatches.length&&<div className="public-lazy-sentinel" ref={loadMoreRef} role="status"><span>Visar {visibleCount} av {filteredMatches.length} matcher</span><button type="button" onClick={()=>setVisibleCount(count=>Math.min(count+18,filteredMatches.length))}>Visa fler</button></div>}</>:<article className="empty-state"><strong>{matchView==="results"?"Inga resultat rapporterade ännu.":"Inga kommande matcher publicerade."}</strong></article>}</section>}
    {tab==="table"&&showTables&&<section><div className="section-heading"><h2>Tabeller</h2><p>Ställningen i cupens grupper, uppdaterad med publicerade resultat.</p></div><PlacementTables groups={placementGroups}/>{standingsLoading?<article className="empty-state"><strong>Hämtar tabeller…</strong></article>:standings.length?<div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows} destinations={playoffDestinations} positionDestinations={playoffPositionMap}/>)}</div>:<article className="empty-state"><strong>Inga tabeller ännu</strong><p>Tabeller visas när grupper och matcher har skapats.</p></article>}</section>}
    {tab==="stats"&&statsEnabled&&<section><div className="section-heading"><span>STATISTIK</span><h2>Topplistor</h2><p>Registrerade matchhändelser direkt från CupNavi.</p></div>{statisticsLoading&&!statistics?<article className="empty-state"><strong>Hämtar topplistor…</strong></article>:statistics?<div className="table-stack">{statistics.enabled.scorers&&<StatisticsTable title="Målskyttar" metric="Mål" rows={statistics.scorers}/>} {statistics.enabled.assists&&<StatisticsTable title="Assistliga" metric="Assist" rows={statistics.assists}/>} {statistics.enabled.cards&&<StatisticsTable title="Spelarkort" metric="Gula/Röda" rows={statistics.cards}/>} {statistics.enabled.fairness&&<DisciplineTable stats={statistics}/>}</div>:<article className="empty-state"><strong>Topplistor kunde inte hämtas just nu.</strong></article>}</section>}

    {tab==="playoff"&&showPlayoffs&&<section><div className="section-heading"><span>SLUTSPEL</span><h2>{hasPlacementGroups?"Placeringsgruppspel":"Vägen till finalen"}</h2><p>{hasPlacementGroups?"Alla möter alla inom sin grupp. Oavgjort är tillåtet och tabellen avgör placeringarna.":"Slutspelet match för match."}</p></div><PlacementTables groups={placementGroups}/>{cup.brackets.length?<div className="table-stack">{cup.brackets.map(bracket=><section key={bracket.id}><div className="subsection-label"><span>SLUTSPEL</span><strong>{hasPlacementGroups?"Placeringsmatcher":bracket.name}</strong></div>{bracket.matches?.length?<div className="match-grid">{bracket.matches.map((match,index)=><MatchCard key={match.id} weather={matchWeather(match)} match={match} teams={cup.teams} groups={cup.groups} pitches={cup.pitches||[]} index={matchNumberById.get(match.id)??index}/>)}</div>:<article className="empty-state"><strong>Matcher kommer när slutspelsträdet är publicerat.</strong></article>}</section>)}</div>:<article className="empty-state"><strong>Inget slutspel är publicerat ännu.</strong></article>}</section>}

    {tab==="info"&&<section className="public-info-v3"><div className="public-info-hero public-info-hero--visitor"><div><span>Cupinfo</span><h2>{cup.tournament.name}</h2><p>{visitorInfoText||"Här finns det viktigaste för publik, spelare och ledare under cupdagen."}</p></div><div className="public-info-hero__facts"><b>{cup.teams.length}<small>Lag</small></b><b>{orderedMatches.length}<small>Matcher</small></b><b>{scheduledPitchCount}<small>Planer</small></b></div></div><div className="public-info-grid public-info-grid--visitor">
      <article className="public-info-card public-info-card--visit"><span className="public-info-card__eyebrow">När & var</span><h3>Hitta rätt från start</h3><div className="public-info-details"><div><span>Datum</span><b>{formatDateRange(cup.tournament.start_date,cup.tournament.end_date)}</b></div>{firstScheduledMatch&&<div><span>Första match</span><b>{formatDateTime(firstScheduledMatch.scheduled_start)}</b></div>}{cup.tournament.arena_address&&<div><span>Plats</span><b>{cup.tournament.arena_address}</b></div>}{cup.tournament.organizer&&<div><span>Arrangör</span><b>{cup.tournament.organizer}</b></div>}</div></article>
      <article className="public-info-card public-info-card--overview"><span className="public-info-card__eyebrow">Cupupplägg</span><h3>{isMatchcamp?"Matchcamp":"Turnering"}</h3><div className="public-info-details"><div><span>Grupper</span><b>{cup.groups.length}</b></div><div><span>Matcher</span><b>{orderedMatches.length}</b></div>{showTables&&<div><span>Tabeller</span><b>Resultat räknas</b></div>}{showPlayoffs&&<div><span>Slutspel</span><b>{cup.brackets.map(bracket=>bracket.name).filter(Boolean).join(", ")||`${cup.brackets.length} slutspel`}</b></div>}</div></article>
      <article className="public-info-card public-info-card--rules"><span className="public-info-card__eyebrow">Regler</span><h3>{isMatchcamp?"Så spelas matcherna":"Så avgörs cupen"}</h3><div className="public-rule-list">
        {hasMatchDuration&&<div><span>Matchtid</span><b>{matchHalves} × {matchMinutesPerHalf} min</b></div>}
        {halftimeMinutes>0&&<div><span>Paus</span><b>{halftimeMinutes} min</b></div>}
        {!isMatchcamp&&<div><span>Poäng</span><b>{cup.tournament.points_win??3} / {cup.tournament.points_draw??1} / {cup.tournament.points_loss??0}</b><small>vinst / oavgjort / förlust</small></div>}
        {!isMatchcamp&&<div><span>Tabellskiljning</span><b>{cup.tournament.table_tiebreak||"Målskillnad först"}</b></div>}
        {(cup.tournament.minimum_team_rest_minutes??0)>0&&<div><span>Minsta vila</span><b>{cup.tournament.minimum_team_rest_minutes} min</b></div>}
        {(cup.tournament.pitch_break_minutes??0)>0&&<div><span>Planpaus</span><b>{cup.tournament.pitch_break_minutes} min</b></div>}
        {Boolean(cup.tournament.avoid_consecutive_matches)&&<div><span>Raka matcher</span><b>Undviks</b>{(cup.tournament.consecutive_match_break_minutes??0)>0&&<small>extra vila {cup.tournament.consecutive_match_break_minutes} min</small>}</div>}
      </div></article>
      <article className="public-info-card public-info-card--contact"><span className="public-info-card__eyebrow">Kontakt</span><h3>Behöver du fråga något?</h3><div className="public-info-details">{cup.tournament.organizer_phone&&<div><span>Telefon</span><b><a href={`tel:${cup.tournament.organizer_phone}`}>{cup.tournament.organizer_phone}</a></b></div>}{cup.tournament.feedback_email&&<div><span>E-post</span><b><a href={`mailto:${cup.tournament.feedback_email}`}>{cup.tournament.feedback_email}</a></b></div>}{!cup.tournament.organizer_phone&&!cup.tournament.feedback_email&&<div><span>Kontakt</span><b>Fråga arrangören på plats</b></div>}</div></article>
      {(cup.pitches||[]).length>0&&<article className="public-info-card"><span className="public-info-card__eyebrow">Planer</span><h3>Spelområdet</h3><div className="public-pitch-list">{(cup.pitches||[]).map(pitch=>{const start=pitch.opens_at||pitch.start_time||pitch.available_from;const end=pitch.closes_at||pitch.end_time||pitch.available_to;return <div key={pitch.pitch_number}><span><b>{pitch.name||`Plan ${pitch.pitch_number}`}</b><small>Plan {pitch.pitch_number}</small></span>{(start||end)&&<strong>{start||"-"}{end?`-${end}`:""}</strong>}</div>})}</div></article>}
      {showPlayoffs&&<article className="public-info-card public-info-card--playoff"><span className="public-info-card__eyebrow">Slutspel</span><h3>{hasPlacementGroups?"Så avgörs cupen":"Vägen vidare"}</h3>{hasPlacementGroups&&<p>Oavgjort är tillåtet. Ingen förlängning eller straffläggning. Vinnaren i ettornas grupp vinner cupen; övriga grupper avgör sina placeringar.</p>}{!hasPlacementGroups&&cup.tournament.playoff_format&&<p>{cup.tournament.playoff_format}</p>}<div className="public-playoff-list">{cup.brackets.map((bracket,index)=><div key={bracket.id}><i className={["is-leading","is-neutral","is-playoff","is-sky"][index]||"is-neutral"}/><span><b>{bracket.name}</b>{(bracket.qualification_rule||bracket.source_rule)&&<small>{bracket.qualification_rule||bracket.source_rule}</small>}</span>{bracket.size&&<small>{bracket.size} lag</small>}</div>)}</div>{!hasPlacementGroups&&cup.tournament.bronze_match&&<div className="public-info-note">Bronsmatch spelas.</div>}</article>}
      {practicalPoints.map(point=><article className="public-info-card" key={point.id}><span className="public-info-card__eyebrow">{(point.kind||"Praktiskt").toUpperCase()}</span><h3>{point.label||"Bra att veta"}</h3>{point.detail&&<p>{point.detail}</p>}{point.url&&<a href={point.url} target="_blank" rel="noreferrer">Öppna karta / länk →</a>}</article>)}
      {showPublicWeather&&<WeatherShareCard address={cup.tournament.arena_address} startDate={cup.tournament.start_date} endDate={cup.tournament.end_date} cupName={cup.tournament.name}/>}
    </div></section>}

    {moreOpen&&<div className="mobile-more-menu" role="dialog" aria-label="Fler cupvyer"><strong>Fler val</strong>{statsEnabled&&<button onClick={()=>openTab("stats")}>★ Topplistor</button>}<button onClick={()=>openTab("info")}>ⓘ Cupinfo & karta</button></div>}
    <nav className="mobile-bottom-nav" aria-label="Snabbnavigation">{mobileItems.map(([key,label,icon])=><button key={key} className={tab===key?"is-active":""} onClick={()=>openTab(key)}><span>{icon}</span>{label}</button>)}<button className={moreOpen||tab==="stats"||tab==="info"?"is-active":""} aria-expanded={moreOpen} onClick={()=>setMoreOpen(value=>!value)}><span>{tab==="info"?"ⓘ":tab==="stats"?"★":"•••"}</span>{tab==="info"?"Cupinfo":tab==="stats"?"Topplistor":"Mer"}</button></nav>
  </main>;
}
