export type RefereeResultPayload={home_score:number;away_score:number;home_penalties:number|null;away_penalties:number|null;expected_home_score:number|null;expected_away_score:number|null;expected_home_penalties:number|null;expected_away_penalties:number|null};
export type RefereeMutation={id:string;cupId:number;matchId:number;createdAt:number;state:"queued"|"uncertain"|"conflict";payload:RefereeResultPayload};

const QUEUE_KEY="cupnavi_referee_queue_v1";
export const REFEREE_QUEUE_EVENT="cupnavi:referee-queue";

export function readRefereeQueue():RefereeMutation[]{
 if(typeof window==="undefined")return [];
 try{const value=JSON.parse(localStorage.getItem(QUEUE_KEY)||"[]");return Array.isArray(value)?value:[]}catch{return []}
}

export function writeRefereeQueue(queue:RefereeMutation[]){
 if(typeof window==="undefined")return;
 localStorage.setItem(QUEUE_KEY,JSON.stringify(queue));
 window.dispatchEvent(new CustomEvent(REFEREE_QUEUE_EVENT));
}

export function upsertRefereeMutation(mutation:RefereeMutation){
 const queue=readRefereeQueue();
 const index=queue.findIndex(item=>item.id===mutation.id);
 if(index>=0){
  const current=queue[index];
  mutation.payload.expected_home_score=current.payload.expected_home_score;
  mutation.payload.expected_away_score=current.payload.expected_away_score;
  mutation.payload.expected_home_penalties=current.payload.expected_home_penalties;
  mutation.payload.expected_away_penalties=current.payload.expected_away_penalties;
  queue[index]=mutation;
 }else queue.push(mutation);
 writeRefereeQueue(queue);
}

export function completeRefereeMutation(processed:RefereeMutation){
 const queue=readRefereeQueue();
 const index=queue.findIndex(item=>item.id===processed.id);
 if(index<0)return;
 const current=queue[index];
 if(current.createdAt===processed.createdAt){queue.splice(index,1);writeRefereeQueue(queue);return}
 current.payload.expected_home_score=processed.payload.home_score;
 current.payload.expected_away_score=processed.payload.away_score;
 current.payload.expected_home_penalties=processed.payload.home_penalties;
 current.payload.expected_away_penalties=processed.payload.away_penalties;
 if(current.payload.home_score===processed.payload.home_score&&current.payload.away_score===processed.payload.away_score&&current.payload.home_penalties===processed.payload.home_penalties&&current.payload.away_penalties===processed.payload.away_penalties)queue.splice(index,1);
 writeRefereeQueue(queue);
}

export function removeRefereeMutation(id:string){writeRefereeQueue(readRefereeQueue().filter(item=>item.id!==id));}
export function updateRefereeMutation(id:string,patch:Partial<RefereeMutation>){writeRefereeQueue(readRefereeQueue().map(item=>item.id===id?({...item,...patch} as RefereeMutation):item));}
export function pendingRefereeCount(cupId?:number){return readRefereeQueue().filter(item=>(cupId==null||item.cupId===cupId)&&item.state!=="conflict").length;}
export function conflictRefereeCount(cupId?:number){return readRefereeQueue().filter(item=>(cupId==null||item.cupId===cupId)&&item.state==="conflict").length;}
export function isNetworkError(error:unknown){return error instanceof TypeError||(!navigator.onLine);}
