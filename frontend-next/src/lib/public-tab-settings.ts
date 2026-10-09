import type { Tournament } from "./types";

export type PublicTab="matches"|"table"|"stats"|"playoff"|"info"|"offers";

export function publicTabSettings(cup:Pick<Tournament,"show_public_info"|"show_public_offers">) {
  return {
    info:cup.show_public_info!==false&&cup.show_public_info!==0,
    offers:cup.show_public_offers!==false&&cup.show_public_offers!==0,
  };
}

export function visiblePublicTab(tab:PublicTab,settings:ReturnType<typeof publicTabSettings>):PublicTab {
  return tab==="info"&&!settings.info||tab==="offers"&&!settings.offers?"matches":tab;
}

const PUBLIC_CUP_UPDATE_KEY="cupnavi:public-cup-update";

// Notify other open tabs only after an admin save has succeeded. No draft,
// credentials or cup content is shared; visitors reread the public API.
export function notifyPublicCupUpdate(cupId:number):void {
  const update={cupId,changedAt:Date.now(),nonce:Math.random()};
  try{localStorage.setItem(PUBLIC_CUP_UPDATE_KEY,JSON.stringify(update));}catch{}
  window.dispatchEvent(new CustomEvent(PUBLIC_CUP_UPDATE_KEY,{detail:update}));
}

export function subscribePublicCupUpdates(cupId:number,onUpdate:()=>void):()=>void {
  const accept=(value:unknown)=>{
    if(value&&typeof value==="object"&&"cupId" in value&&value.cupId===cupId)onUpdate();
  };
  const onStorage=(event:StorageEvent)=>{
    if(event.key!==PUBLIC_CUP_UPDATE_KEY||!event.newValue)return;
    try{accept(JSON.parse(event.newValue));}catch{}
  };
  const onLocal=(event:Event)=>accept((event as CustomEvent).detail);
  window.addEventListener("storage",onStorage);
  window.addEventListener(PUBLIC_CUP_UPDATE_KEY,onLocal);
  return()=>{window.removeEventListener("storage",onStorage);window.removeEventListener(PUBLIC_CUP_UPDATE_KEY,onLocal);};
}
