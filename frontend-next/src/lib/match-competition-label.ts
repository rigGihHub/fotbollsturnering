import type { Bracket, Group, Match, PlacementGroup } from "./types";

function displayName(value?:string|null):string {
  const name=(value||"").trim().replace(/\s+/g," ");
  return name&&name===name.toLocaleUpperCase("sv-SE")
    ? name[0]+name.slice(1).toLocaleLowerCase("sv-SE")
    : name;
}

function playoffDetail(value?:string|null):string {
  const name=displayName(value);
  if(/^(slutspel|importerat slutspel|playoff|gruppspel)$/i.test(name))return "";
  return name.replace(/^slutspel\s*[·:–-]\s*/i,"");
}

export function matchCompetitionLabel(
  match:Match,
  groups:Group[]=[],
  brackets:Bracket[]=[],
  placementGroups:PlacementGroup[]=[],
):string {
  const placement=placementGroups.find(group=>group.match_ids?.includes(match.id));
  const bracket=(match.bracket_id==null?undefined:brackets.find(item=>item.id===match.bracket_id))
    ||brackets.find(item=>item.matches?.some(row=>row.id===match.id));
  if(match.bracket_id!=null||bracket||placement){
    const placementName=playoffDetail(placement?.name);
    if(placementName)return `Slutspel · ${placementName}`;
    const details=[playoffDetail(bracket?.name),playoffDetail(match.stage)]
      .filter((name,index,all)=>name&&all.findIndex(other=>other.toLocaleLowerCase("sv-SE")===name.toLocaleLowerCase("sv-SE"))===index);
    return ["Slutspel",...details].join(" · ");
  }
  const groupName=groups.find(group=>group.id===match.group_id)?.name.trim()||"";
  return /^[A-ZÅÄÖ]$/i.test(groupName)?`Grupp ${groupName.toUpperCase()}`:groupName;
}
