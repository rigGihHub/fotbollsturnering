import type { RevisionChange, RevisionSchedule } from "./schedule-revision-review";

export function revisionCommitRows(selected:RevisionChange[]){
  return selected.map(row=>({match_id:row.match.id,scheduled_start:row.nextStart,pitch_number:row.nextPitch,expected_scheduled_start:row.match.scheduled_start||null,expected_pitch_number:row.match.pitch_number??null}));
}

export function revisionIsSaved(selected:RevisionChange[],schedule?:RevisionSchedule|null){
  return !!schedule&&selected.length>0&&selected.every(change=>{
    const match=schedule.matches.find(row=>row.id===change.match.id);
    return !!match&&(match.scheduled_start||"").replace(" ","T").slice(0,16)===change.nextStart&&match.pitch_number===change.nextPitch;
  });
}
