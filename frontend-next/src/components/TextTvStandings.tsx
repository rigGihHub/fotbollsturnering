import { StandingRow } from "@/lib/types";

export function TextTvStandings({ name, rows }: { name: string; rows: StandingRow[] }) {
  return (
    <section className="texttv" aria-labelledby={`table-${name}`}>
      <div className="texttv__header"><span>330</span><strong id={`table-${name}`}>{name.toUpperCase()}</strong><span>LIVE TABELL</span></div>
      <div className="texttv__scroll">
        <table>
          <thead><tr><th>PL</th><th>LAG</th><th>S</th><th>V</th><th>O</th><th>F</th><th>MS</th><th>P</th></tr></thead>
          <tbody>{rows.map((row)=><tr key={row.team_id}><td>{row.position}</td><td>{row.Lag}</td><td>{row.S}</td><td>{row.V}</td><td>{row.O}</td><td>{row.F}</td><td>{row.MS}</td><td><strong>{row.P}</strong></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
