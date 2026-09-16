export type EventValues={goals:number;assists:number;yellow_cards:number;red_cards:number};

export type ReporterMutation=
 | {id:string;kind:"result";cupId:number;matchId:number;createdAt:number;state:"queued"|"uncertain"|"conflict";payload:{home_score:number;away_score:number;home_penalties:number|null;away_penalties:number|null;expected_home_score:number|null;expected_away_score:number|null;expected_home_penalties:number|null;expected_away_penalties:number|null}}
 | {id:string;kind:"event";cupId:number;matchId:number;playerId:number;createdAt:number;state:"queued"|"uncertain"|"conflict";payload:EventValues&{expected:EventValues}};
export type ResultMutation=Extract<ReporterMutation,{kind:"result"}>;
export type EventMutation=Extract<ReporterMutation,{kind:"event"}>;
export const isResultMutation=(item:ReporterMutation):item is ResultMutation=>item.kind==="result";
export const isEventMutation=(item:ReporterMutation):item is EventMutation=>item.kind==="event";

const QUEUE_KEY="cupnavi_reporter_queue_v1";
const CACHE_KEY="cupnavi_reporter_cache_v1";
export const QUEUE_EVENT="cupnavi:reporter-queue";

export function readReporterQueue():ReporterMutation[]{
 if(typeof window==="undefined")return [];
 try{const value=JSON.parse(localStorage.getItem(QUEUE_KEY)||"[]");return Array.isArray(value)?value:[]}catch{return []}
}

export function writeReporterQueue(queue:ReporterMutation[]){
 if(typeof window==="undefined")return;
 localStorage.setItem(QUEUE_KEY,JSON.stringify(queue));
 window.dispatchEvent(new CustomEvent(QUEUE_EVENT));
}

export function upsertReporterMutation(mutation:ReporterMutation){
 const queue=readReporterQueue();
 const index=queue.findIndex(item=>item.id===mutation.id);
 if(index>=0){
  const current=queue[index];
  if(current.kind===mutation.kind){
   // Behåll serverbaslinjen vid flera offline-tryck; endast önskat slutläge ändras.
   if(current.kind==="event"&&mutation.kind==="event")mutation.payload.expected=current.payload.expected;
   if(current.kind==="result"&&mutation.kind==="result"){
    mutation.payload.expected_home_score=current.payload.expected_home_score;
    mutation.payload.expected_away_score=current.payload.expected_away_score;
    mutation.payload.expected_home_penalties=current.payload.expected_home_penalties;
    mutation.payload.expected_away_penalties=current.payload.expected_away_penalties;
   }
  }
  queue[index]=mutation;
 }else queue.push(mutation);
 writeReporterQueue(queue);
}

export function removeReporterMutation(id:string){writeReporterQueue(readReporterQueue().filter(item=>item.id!==id));}
export function updateReporterMutation(id:string,patch:Partial<ReporterMutation>){writeReporterQueue(readReporterQueue().map(item=>item.id===id?({...item,...patch} as ReporterMutation):item));}
export function pendingReporterCount(cupId?:number){return readReporterQueue().filter(item=>cupId==null||item.cupId===cupId).length;}

export function writeReporterCache<T>(key:string,value:T){
 if(typeof window==="undefined")return;
 try{const cache=JSON.parse(localStorage.getItem(CACHE_KEY)||"{}");cache[key]={savedAt:Date.now(),value};localStorage.setItem(CACHE_KEY,JSON.stringify(cache))}catch{}
}

export function readReporterCache<T>(key:string):T|null{
 if(typeof window==="undefined")return null;
 try{return JSON.parse(localStorage.getItem(CACHE_KEY)||"{}")[key]?.value??null}catch{return null}
}

export function isNetworkError(error:unknown){return error instanceof TypeError||(!navigator.onLine);}
export const sameEventValues=(a:EventValues,b:EventValues)=>a.goals===b.goals&&a.assists===b.assists&&a.yellow_cards===b.yellow_cards&&a.red_cards===b.red_cards;
