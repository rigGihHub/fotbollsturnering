import { Tournament } from "@/lib/types";
import { dateLabel } from "@/lib/format";

export function CupCover({ tournament, teamCount, matchCount, groupCount }: { tournament: Tournament; teamCount: number; matchCount:number; groupCount:number }) {
  return (
    <header className="cn-cup-cover" aria-labelledby="cup-title">
      <div className="cn-cup-cover__main">
        <p className="cn-cup-cover__label">{tournament.arrangement_type==="matchcamp"?"Matchcamp":"Turnering"}</p>
        <h1 id="cup-title">{tournament.name}</h1>
        <p className="cn-cup-cover__meta"><span>{dateLabel(tournament.start_date)}</span><span>{tournament.arena_address||"Plats kommer"}</span></p>
      </div>
      <div className="cn-cup-cover__stats" aria-label="Cupöversikt">
        <span><b>{teamCount}</b><small>lag</small></span>
        <span><b>{matchCount}</b><small>matcher</small></span>
        {groupCount>0&&<span><b>{groupCount}</b><small>grupper</small></span>}
      </div>
    </header>
  );
}
