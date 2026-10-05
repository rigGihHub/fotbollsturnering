import type { PublicPartners } from "@/lib/api";

export function PublicOffers({partners,loading,error,onRetry}:{partners:PublicPartners|null;loading:boolean;error:boolean;onRetry:()=>void}) {
  const offers=partners?.offers||[];
  const sponsors=partners?.sponsors||[];
  const sponsorByName=new Map(sponsors.map(sponsor=>[sponsor.name.trim().toLocaleLowerCase("sv"),sponsor]));

  return <section className="cn-offers-page" aria-labelledby="cn-offers-title">
    <header className="cn-offers-hero">
      <span className="cn-offers-eyebrow">CUPENS PARTNERS</span>
      <h2 id="cn-offers-title">Erbjudanden</h2>
      <p>Här hittar du erbjudanden från företag och föreningar som samarbetar med cupen.</p>
    </header>

    {loading&&!partners&&<div className="cn-offers-empty" role="status">Hämtar erbjudanden…</div>}
    {error&&<div className="cn-offers-empty" role="alert"><strong>{partners?"Erbjudandena kunde inte uppdateras. Visar senast hämtade uppgifter.":"Erbjudandena kunde inte hämtas."}</strong><button type="button" onClick={onRetry}>Försök igen</button></div>}
    {partners&&<>
      {offers.length>0?<div className="cn-offers-grid">{offers.map(offer=>{
        const sponsor=sponsorByName.get((offer.business_name||"").trim().toLocaleLowerCase("sv"));
        return <article className="cn-offer-card" key={offer.id}>
          <div className="cn-offer-card__top"><span>ERBJUDANDE</span>{offer.valid_until&&<small>Gäller till {offer.valid_until}</small>}</div>
          {sponsor?.logo_data_uri&&<img className="cn-offer-card__logo" src={sponsor.logo_data_uri} alt={`${sponsor.name} logotyp`} loading="lazy"/>}
          {offer.business_name&&<p className="cn-offer-card__business">{offer.business_name}</p>}
          <h3>{offer.title}</h3>
          {offer.description&&<p className="cn-offer-card__description">{offer.description}</p>}
          {offer.discount_code&&<div className="cn-offer-card__code"><span>Rabattkod</span><strong>{offer.discount_code}</strong></div>}
          {offer.url&&<a className="cn-offer-card__link" href={offer.url} target="_blank" rel="noopener noreferrer">Visa erbjudandet <span aria-hidden="true">↗</span></a>}
        </article>;
      })}</div>:<div className="cn-offers-empty"><strong>Inga erbjudanden publicerade ännu</strong><p>Arrangören kan lägga till erbjudanden inför cupen.</p></div>}

    </>}
  </section>;
}
