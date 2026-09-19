import { StandingRow } from "@/lib/types";

export function TextTvStandings({ name, rows }: { name: string; rows: StandingRow[] }) {
  const tone=(index:number)=>index<2?"is-leading":index===2?"is-playoff":rows.length>5&&index>=rows.length-2?"is-bottom":"";
  return (
    <section className="texttv texttv--standings" aria-labelledby={`table-${name}`}>
      <div className="texttv__header texttv__header--group"><strong id={`table-${name}`}>{name}</strong></div>
      <div className="texttv__scroll">
        <table>
          <thead><tr><th>PL</th><th>LAG</th><th>S</th><th>V</th><th>O</th><th>F</th><th>MS</th><th>P</th></tr></thead>
          <tbody>{rows.map((row,index)=><tr className={tone(index)} key={row.team_id}><td>{row.position}</td><td>{row.Lag}</td><td>{row.S}</td><td>{row.V}</td><td>{row.O}</td><td>{row.F}</td><td>{row.MS}</td><td><strong>{row.P}</strong></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
