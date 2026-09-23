import type { CupSnapshot, Match } from './types';
import { matchStatus, sourceTeamId } from './format';

export function cupMatches(cup:CupSnapshot):Match[] {
  const matches=new Map<number,Match>();
  for(const match of [...cup.matches,...cup.brackets.flatMap(bracket=>bracket.matches||[])])matches.set(match.id,match);
  return [...matches.values()].sort((a,b)=>(Date.parse(a.scheduled_start||'')||Infinity)-(Date.parse(b.scheduled_start||'')||Infinity)||a.id-b.id);
}
export function belongsToTeam(match:Match,teamId:number):boolean {
  return [match.home_participant?.team_id,match.away_participant?.team_id,sourceTeamId(match.home_source),sourceTeamId(match.away_source)].includes(teamId);
}
export function matchdayOrder(matches:Match[]):Match[] {
  const live=matches.filter(match=>['live','halftime'].includes(matchStatus(match)));
  const upcoming=matches.filter(match=>matchStatus(match)==='next');
  const finished=matches.filter(match=>matchStatus(match)==='done').reverse();
  return [...live,...upcoming,...finished];
}
export function hasPlayoffs(cup:CupSnapshot):boolean {
  return cup.tournament.arrangement_type!=='matchcamp' && (cup.brackets.length>0 || Boolean(cup.placement_groups?.length));
}
