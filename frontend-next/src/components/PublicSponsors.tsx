"use client";

import { useState } from "react";
import type { PublicPartners } from "@/lib/api";

function Sponsor({sponsor}:{sponsor:PublicPartners["sponsors"][number]}) {
  const [failedLogo,setFailedLogo]=useState<string|null>(null);
  return <div className="cn-info-sponsor">
    {sponsor.logo_data_uri&&failedLogo!==sponsor.logo_data_uri&&<img src={sponsor.logo_data_uri} alt={`${sponsor.name} logotyp`} loading="lazy" onError={()=>setFailedLogo(sponsor.logo_data_uri||null)}/>}
    <div><h4>{sponsor.name}</h4>{sponsor.description&&<p>{sponsor.description}</p>}{sponsor.website_url&&<a href={sponsor.website_url} target="_blank" rel="noopener noreferrer">Besök webbplats <span aria-hidden="true">↗</span></a>}</div>
  </div>;
}

export function PublicSponsors({partners,loading,error,onRetry}:{partners:PublicPartners|null;loading:boolean;error:boolean;onRetry:()=>void}) {
  return <article className="public-info-card cn-info-sponsors" aria-labelledby="cn-info-sponsors-title">
    <span className="public-info-card__eyebrow">Cupens samarbeten</span>
    <h3 id="cn-info-sponsors-title">Sponsorer</h3>
    {loading&&!partners&&<p role="status">Hämtar sponsorer…</p>}
    {error&&<div className="cn-info-sponsors__status" role="alert"><p>{partners?"Sponsorerna kunde inte uppdateras. Visar senast hämtade uppgifter.":"Sponsorerna kunde inte hämtas."}</p><button type="button" onClick={onRetry}>Försök igen</button></div>}
    {partners&&(partners.sponsors.length?<div className="cn-info-sponsors__list">{partners.sponsors.map(sponsor=><Sponsor key={sponsor.id} sponsor={sponsor}/>)}</div>:<p>Inga sponsorer publicerade ännu.</p>)}
  </article>;
}
