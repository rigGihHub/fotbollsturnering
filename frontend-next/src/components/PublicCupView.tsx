"use client";

import { useMemo, useState } from "react";
import { CupSnapshot, StandingRow } from "@/lib/types";
import { CupCover } from "./CupCover";
import { MatchCard } from "./MatchCard";
import { TextTvStandings } from "./TextTvStandings";

type StandingsGroup = {group:{id:number;name:string};rows:StandingRow[]};

export function PublicCupView({ cup, standings }: { cup: CupSnapshot; standings: StandingsGroup[] }) {
  const [tab, setTab] = useState<"matches"|"table"|"playoff"|"info">("matches");
  const upcoming = useMemo(()=>cup.matches.slice(0, 12), [cup.matches]);
  return (
    <main className="page-shell">
      <CupCover tournament={cup.tournament} teamCount={cup.teams.length} />
      <nav className="edition-nav" aria-label="Cupens innehåll">
        {[["matches","Matcher"],["table","Tabeller"],["playoff","Slutspel"],["info","Cupinfo"]].map(([key,label], index)=>(
          <button key={key} className={tab===key?"is-active":""} onClick={()=>setTab(key as typeof tab)}><span>0{index+1}</span>{label}</button>
        ))}
      </nav>
      {tab === "matches" && <section><div className="section-heading"><span>MATCHDAY CARDS</span><h2>Matcher</h2><p>Programmet som samlarkort. Resultatet får sin egen Text-TV-ruta.</p></div><div className="match-grid">{upcoming.map((match,index)=><MatchCard key={match.id} match={match} teams={cup.teams} index={index}/>)}</div></section>}
      {tab === "table" && <section><div className="section-heading"><span>TEXT-TV 330</span><h2>Tabeller</h2><p>CupNavis mörka live-lager är reserverat för resultat och statistik.</p></div><div className="table-stack">{standings.map(item=><TextTvStandings key={item.group.id} name={item.group.name} rows={item.rows}/>)}</div></section>}
      {tab === "playoff" && <section><div className="section-heading"><span>THE BRACKET ISSUE</span><h2>Slutspel</h2></div><div className="bracket-grid">{cup.brackets.map((bracket)=><article className="feature-card" key={bracket.id}><span className="feature-card__number">BR//{String(bracket.id).padStart(2,"0")}</span><h3>{bracket.name}</h3><p>{bracket.matches?.length || 0} publicerade matcher</p></article>)}</div></section>}
      {tab === "info" && <section><div className="section-heading"><span>CUP GUIDE</span><h2>Cupinfo</h2></div><article className="editorial-card"><h3>{cup.tournament.organizer || "Arrangören"}</h3><p>{cup.tournament.public_information || "Ingen publik information är publicerad ännu."}</p><div className="editorial-card__meta">{cup.tournament.arena_address || "Plats kommer"}</div></article></section>}
    </main>
  );
}
