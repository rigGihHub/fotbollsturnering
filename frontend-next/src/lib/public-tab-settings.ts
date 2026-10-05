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
