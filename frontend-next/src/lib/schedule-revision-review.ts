export type ImportedMatch={time?:string|null;venue?:string|null;group_name?:string|null;home_team?:string|null;away_team?:string|null};
export type RevisionProposal={matches?:ImportedMatch[];source_name?:string|null;warnings?:string[]};
export type RevisionMatch={id:number;home_label:string;away_label:string;group_name?:string|null;scheduled_start?:string|null;pitch_number?:number|null;schedule_locked:boolean;played:boolean};
export type RevisionSchedule={matches:RevisionMatch[];start_date?:string|null;end_date?:string|null};
export type RevisionPitch={pitch_number:number;name:string};
export type RevisionChange={match:RevisionMatch;nextStart:string;nextPitch:number;selected:boolean};
export type RevisionReview={changes:RevisionChange[];unchanged:number;unmatched:string[];warnings:string[];preserved:string[]};

function norm(value?:string|null){return (value||"").trim().toLocaleLowerCase("sv").replace(/\s+/g," ");}
function startValue(raw:string|undefined|null,schedule:RevisionSchedule){
  let value=(raw||"").trim();
  if(/^\d{1,2}[:.]\d{2}$/.test(value)){
    if(!schedule.start_date||(schedule.end_date&&schedule.end_date!==schedule.start_date))return null;
    value=`${schedule.start_date}T${value.replace(".",":").padStart(5,"0")}`;
  }
  const parts=/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::00)?$/.exec(value);
  if(!parts||Number(parts[2])>23||Number(parts[3])>59)return null;
  const date=new Date(`${parts[1]}T00:00:00Z`);
  if(Number.isNaN(date.getTime())||date.toISOString().slice(0,10)!==parts[1])return null;
  if(schedule.start_date&&parts[1]<schedule.start_date)return null;
  if(schedule.end_date&&parts[1]>schedule.end_date)return null;
  return `${parts[1]}T${parts[2]}:${parts[3]}`;
}

export function reviewScheduleRevision(proposal:RevisionProposal,schedule:RevisionSchedule,pitches:RevisionPitch[]):RevisionReview {
  const changes:RevisionChange[]=[],unmatched:string[]=[],preserved:string[]=[];
  let unchanged=0;
  const resolved=new Map<number,{row:ImportedMatch;match:RevisionMatch}>();
  const duplicates=new Set<number>();
  for(const row of proposal.matches||[]){
    const home=norm(row.home_team),away=norm(row.away_team),group=norm(row.group_name);
    if(!home||!away){unmatched.push("En importerad match saknar hemma- eller bortalag.");continue;}
    const candidates=schedule.matches.filter(match=>norm(match.home_label)===home&&norm(match.away_label)===away&&(!group||norm(match.group_name)===group));
    if(candidates.length!==1){unmatched.push(`${row.home_team} – ${row.away_team}: ${candidates.length?"flera möjliga matcher":"ingen exakt match hittades"}.`);continue;}
    const match=candidates[0];
    if(resolved.has(match.id)){duplicates.add(match.id);continue;}
    resolved.set(match.id,{row,match});
  }
  for(const {row,match} of resolved.values()){
    const name=`${match.home_label} – ${match.away_label}`;
    if(duplicates.has(match.id)){unmatched.push(`${name}: flera rader i underlaget gäller samma match. Kontrollera PDF:en.`);continue;}
    if(match.played||match.schedule_locked){preserved.push(`${name}: ${match.played?"redan spelad":"låst"}.`);continue;}
    const nextStart=startValue(row.time,schedule);
    const foundPitches=pitches.filter(pitch=>norm(pitch.name)===norm(row.venue));
    if(!nextStart){unmatched.push(`${name}: datum/tid kan inte bevisas säkert. Flerdagarscuper kräver datum i revisionsunderlaget.`);continue;}
    if(foundPitches.length!==1){unmatched.push(`${name}: planen '${row.venue||"saknas"}' matchar inte en entydig befintlig plan.`);continue;}
    const nextPitch=foundPitches[0].pitch_number;
    if((match.scheduled_start||"").replace(" ","T").slice(0,16)===nextStart&&Number(match.pitch_number||0)===nextPitch){unchanged++;continue;}
    changes.push({match,nextStart,nextPitch,selected:true});
  }
  return {changes,unchanged,unmatched,preserved,warnings:proposal.warnings||[]};
}
