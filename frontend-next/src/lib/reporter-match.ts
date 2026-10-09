import {isResultMutation,isStatusMutation,readReporterQueue} from "./reporter-offline";

export type MatchLifecycle="not_started"|"live"|"halftime"|"finished";
export type ReporterMatch={requires_winner?:boolean;id:number;stage?:string|null;home_team:string;away_team:string;home_score:number|null;away_score:number|null;home_penalties?:number|null;away_penalties?:number|null;status:string;match_status?:MatchLifecycle|null;scheduled_start?:string|null;clock_elapsed_seconds?:number;clock_synced_at?:string|null;actual_started_at?:string|null};
export const reporterMatchLifecycle=(match:ReporterMatch):MatchLifecycle=>match.match_status==="not_started"||match.match_status==="live"||match.match_status==="halftime"||match.match_status==="finished"?match.match_status:match.status==="played"?"finished":"not_started";

export function reporterElapsedSeconds(match:ReporterMatch,now=Date.now()){
 const base=match.clock_elapsed_seconds||0;
 // The server's elapsed value already includes the live segment up to this timestamp.
 const anchor=match.clock_synced_at;
 const extra=reporterMatchLifecycle(match)==="live"&&anchor?Math.max(0,Math.floor((now-Date.parse(anchor))/1000)):0;
 return base+(Number.isFinite(extra)?extra:0);
}

export function reporterStatusProjection(match:ReporterMatch,status:MatchLifecycle,at:number):ReporterMatch{
 return {...match,match_status:status,status:status==="finished"?"played":status,clock_elapsed_seconds:reporterElapsedSeconds(match,at),clock_synced_at:new Date(at).toISOString(),actual_started_at:status==="live"?new Date(at).toISOString():null};
}

export function overlayReporterMatches(matches:ReporterMatch[],cupId:number){
 const queued=readReporterQueue().filter(item=>item.cupId===cupId&&item.state!=="conflict").sort((a,b)=>a.createdAt-b.createdAt);
 return matches.map(match=>{
  let current=match;
  for(const item of queued){
   if(item.matchId!==match.id)continue;
   if(isResultMutation(item))current={...current,home_score:item.payload.home_score,away_score:item.payload.away_score,home_penalties:item.payload.home_penalties,away_penalties:item.payload.away_penalties};
   else if(isStatusMutation(item)&&reporterMatchLifecycle(current)===item.payload.expected_status)current=reporterStatusProjection(current,item.payload.status,item.createdAt);
  }
  return current;
 });
}
