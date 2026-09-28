import type { PlacementGroup } from "./types";

type Tone="is-leading"|"is-neutral"|"is-playoff"|"is-sky";

export function placementStandingsPresentation(rankCount:number, groups:PlacementGroup[]){
  const destinations=groups.filter(group=>Number.isInteger(group.placement)&&Number(group.placement)>0);
  if(!destinations.length||rankCount<1)return null;

  const names=new Map(destinations.map(group=>[Number(group.placement),group.name]));
  const labels=Array.from({length:rankCount},(_,index)=>names.get(index+1)||`Placering ${index+1}`);
  const tones:Tone[]=Array.from({length:rankCount},(_,index)=>{
    if(rankCount===3)return (["is-sky","is-neutral","is-playoff"] as Tone[])[index];
    if(index===0)return "is-leading";
    if(index===rankCount-1)return "is-sky";
    if(index===rankCount-2)return "is-playoff";
    return "is-neutral";
  });
  const positionDestinations=Object.fromEntries(labels.map((_,index)=>[index+1,index]));
  return {destinations:labels,destinationTones:tones,positionDestinations};
}
