import { Tournament } from "@/lib/types";
import { dateLabel } from "@/lib/format";

export function CupCover({ tournament, teamCount, matchCount, groupCount }: { tournament: Tournament; teamCount: number; matchCount:number; groupCount:number }) {
  return (
    <section className="cup-cover" aria-labelledby="cup-title">
      <div className="cup-cover__eyebrow"><span>CN//01</span><span>TOURNAMENT EDITION</span></div>
      <div className="cup-cover__content">
        <div>
          <p className="kicker">CupNavi // Matchday edition</p>
          <h1 id="cup-title">{tournament.name}</h1>
          <p className="cup-cover__meta">
            {tournament.arena_address || "Plats kommer"} <span>•</span> {dateLabel(tournament.start_date)}
          </p>
          <div className="cup-cover__facts"><span><b>{teamCount}</b> lag</span><span><b>{matchCount}</b> matcher</span>{groupCount>0&&<span><b>{groupCount}</b> grupper</span>}</div>
        </div>
        <div className="collectible-stamp" aria-label="CupNavi collector edition">
          <span>CN</span><strong>{String(tournament.id).padStart(3, "0")}</strong>
        </div>
      </div>
      <div className="cup-cover__stripe" aria-hidden="true" />
      <div className="cup-cover__burst" aria-hidden="true">GAME ON</div>
    </section>
  );
}
