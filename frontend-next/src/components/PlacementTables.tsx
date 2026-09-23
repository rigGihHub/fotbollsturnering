import type { ReactNode } from "react";
import type { PlacementGroup } from "../lib/types";
import { TextTvStandings } from "./TextTvStandings";

export function PlacementTables({groups,renderMatches}:{groups:PlacementGroup[];renderMatches?:(group:PlacementGroup)=>ReactNode}) {
  if(!groups.length)return null;
  return <div className="table-stack">{groups.map(group=><section key={`${group.bracket_id}-${group.name}`}>
    {group.placement===1&&<p className="cn-placement-purpose">Vinnaren av denna grupp vinner cupen.</p>}
    <TextTvStandings name={group.name} rows={group.rows}/>
    <p>{group.winner?<><strong>{group.placement===1?"Cupvinnare":"Gruppvinnare"}: {group.winner}</strong></>:group.ranking_tied?"Lagen i toppen är lika. Arrangören behöver avgöra placeringen enligt cupens regler.":group.complete?"Gruppen är färdigspelad.":"Tabellen är preliminär tills alla matcher är färdigspelade."}</p>
    {renderMatches?.(group)}
  </section>)}</div>;
}
