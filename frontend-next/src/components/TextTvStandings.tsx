import { useId } from "react";
import { StandingRow } from "@/lib/types";

export function TextTvStandings({ name, rows, destinations=[], positionDestinations={} }: { name: string; rows: StandingRow[]; destinations?:string[]; positionDestinations?:Record<number,number> }) {
  const id=useId();
  const tones=["is-leading","is-neutral","is-playoff","is-sky"];
  const tone=(index:number)=>tones[index]||"is-neutral";
  const rowTone=(row:StandingRow)=>positionDestinations[row.position]!==undefined?tone(positionDestinations[row.position]):"";
  return (
    <section className="cn-standings" aria-labelledby={id}>
      <div className="cn-standings__header"><strong id={id}>{name}</strong></div>
      <div className="cn-standings__body">
        <table><caption className="cn-sr-only">{name}: placering, lag, spelade, vunna, oavgjorda, förlorade, målskillnad och poäng</caption>
          <thead><tr><th scope="col" aria-label="Placering">#</th><th scope="col">Lag</th><th scope="col" aria-label="Spelade">S</th><th scope="col" aria-label="Vunna">V</th><th scope="col" aria-label="Oavgjorda">O</th><th scope="col" aria-label="Förlorade">F</th><th scope="col" aria-label="Målskillnad">MS</th><th scope="col" aria-label="Poäng">P</th></tr></thead>
          <tbody>{rows.map((row)=><tr className={rowTone(row)} key={row.team_id}><td>{row.position}</td><td><span className="cn-standings__team">{row.Lag}</span>{positionDestinations[row.position]!==undefined&&<small className="cn-standings__destination">{destinations[positionDestinations[row.position]]}</small>}</td><td>{row.S}</td><td>{row.V}</td><td>{row.O}</td><td>{row.F}</td><td>{row.MS}</td><td><strong>{row.P}</strong></td></tr>)}</tbody>
        </table>
      </div>{destinations.length>0&&<div className="cn-standings__legend">{destinations.map((label,index)=><span className={tone(index)} key={`${label}-${index}`}><i/> {label}</span>)}</div>}
    </section>
  );
}
