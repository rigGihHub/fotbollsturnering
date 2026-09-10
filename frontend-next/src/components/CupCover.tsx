import { Tournament } from "@/lib/types";
import { dateLabel } from "@/lib/format";

export function CupCover({ tournament, teamCount }: { tournament: Tournament; teamCount: number }) {
  return (
    <section className="cup-cover" aria-labelledby="cup-title">
      <div className="cup-cover__eyebrow"><span>CN//01</span><span>TOURNAMENT EDITION</span></div>
      <div className="cup-cover__content">
        <div>
          <p className="kicker">CupNavi matchday</p>
          <h1 id="cup-title">{tournament.name}</h1>
          <p className="cup-cover__meta">
            {tournament.arena_address || "Plats kommer"} · {dateLabel(tournament.start_date)} · {teamCount} lag
          </p>
        </div>
        <div className="collectible-stamp" aria-label="CupNavi collector edition">
          <span>CN</span><strong>{String(tournament.id).padStart(3, "0")}</strong>
        </div>
      </div>
      <div className="cup-cover__stripe" aria-hidden="true" />
    </section>
  );
}
