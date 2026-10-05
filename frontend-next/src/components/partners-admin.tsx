"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";

type Sponsor = {id:number;name:string;level:string|null;description:string|null;website_url:string|null;logo_data_uri:string|null;active:number;sort_order:number};
type Offer = {id:number;title:string;business_name:string|null;description:string|null;discount_code:string|null;valid_until:string|null;url:string|null;active:number;sort_order:number};
type Partners = {sponsors:Sponsor[];offers:Offer[]};
const newSponsor={name:"",level:"",description:"",website_url:"",logo_data_uri:"",active:true,sort_order:0};
const newOffer={title:"",business_name:"",description:"",discount_code:"",valid_until:"",url:"",active:true,sort_order:0};
const sponsorDraft=(value?:Sponsor)=>({...newSponsor,...value,level:value?.level||"",description:value?.description||"",website_url:value?.website_url||"",logo_data_uri:value?.logo_data_uri||"",active:Boolean(value?.active??true)});
const offerDraft=(value?:Offer)=>({...newOffer,...value,business_name:value?.business_name||"",description:value?.description||"",discount_code:value?.discount_code||"",valid_until:value?.valid_until||"",url:value?.url||"",active:Boolean(value?.active??true)});

async function req<T>(path:string,token:string,options:RequestInit={}):Promise<T> {
  const headers=new Headers(options.headers||{});
  headers.set("Authorization",`Bearer ${token}`);
  if(options.body)headers.set("Content-Type","application/json");
  const response=await fetch(`${CLIENT_API_BASE}${path}`,{...options,headers,cache:"no-store"});
  const data=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(data?.detail||`API-fel ${response.status}`);
  return data as T;
}

function SponsorEditor({value,onSave,onDelete,busy}:{value?:Sponsor;onSave:(draft:typeof newSponsor,existing?:Sponsor)=>Promise<boolean>;onDelete?:(item:Sponsor)=>Promise<void>;busy:boolean}) {
  const [draft,setDraft]=useState(sponsorDraft(value));
  const [logoError,setLogoError]=useState("");
  useEffect(()=>setDraft(sponsorDraft(value)),[value]);
  async function logo(file?:File) {
    if(!file)return;
    if(!["image/png","image/jpeg","image/webp"].includes(file.type)||file.size>1_500_000){setLogoError("Välj PNG, JPG eller WEBP på högst 1,5 MB.");return;}
    setLogoError("");
    const reader=new FileReader();
    reader.onload=()=>setDraft(current=>({...current,logo_data_uri:String(reader.result||"")}));
    reader.readAsDataURL(file);
  }
  return <form className="cn-partner-form" onSubmit={async(event:FormEvent)=>{event.preventDefault();if(await onSave(draft,value)&&!value)setDraft({...newSponsor});}}>
    <div className="cn-partner-fields">
      <label className="cn-partner-wide">Sponsorns namn<input required maxLength={150} value={draft.name} onChange={e=>setDraft({...draft,name:e.target.value})}/></label>
      <label>Webbplats<input type="text" placeholder="exempel.se" value={draft.website_url||""} onChange={e=>setDraft({...draft,website_url:e.target.value})}/></label>
      <label>Logotyp<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>void logo(e.target.files?.[0])}/></label>
      {draft.logo_data_uri&&<div className="cn-partner-logo-preview"><img src={draft.logo_data_uri} alt="Förhandsvisning av logotyp"/><button type="button" onClick={()=>setDraft({...draft,logo_data_uri:""})}>Ta bort logotyp</button></div>}
      <label className="cn-partner-wide">Kort beskrivning<textarea maxLength={1000} value={draft.description||""} onChange={e=>setDraft({...draft,description:e.target.value})}/></label>
      <label>Visningsordning<input type="number" min={0} max={999} value={draft.sort_order} onChange={e=>setDraft({...draft,sort_order:Number(e.target.value)})}/></label>
      <label className="cn-partner-check"><input type="checkbox" checked={draft.active} onChange={e=>setDraft({...draft,active:e.target.checked})}/> Visa i turneringsvyn</label>
    </div>
    {logoError&&<p role="alert">{logoError}</p>}
    <div className="cn-partner-actions"><button type="submit" disabled={busy||Boolean(logoError)}>{value?"Spara sponsor":"Lägg till sponsor"}</button>{value&&onDelete&&<button type="button" disabled={busy} onClick={()=>void onDelete(value)}>Ta bort</button>}</div>
  </form>;
}

function OfferEditor({value,onSave,onDelete,busy}:{value?:Offer;onSave:(draft:typeof newOffer,existing?:Offer)=>Promise<boolean>;onDelete?:(item:Offer)=>Promise<void>;busy:boolean}) {
  const [draft,setDraft]=useState(offerDraft(value));
  useEffect(()=>setDraft(offerDraft(value)),[value]);
  return <form className="cn-partner-form" onSubmit={async(event:FormEvent)=>{event.preventDefault();if(await onSave(draft,value)&&!value)setDraft({...newOffer});}}>
    <div className="cn-partner-fields">
      <label>Erbjudandets rubrik<input required maxLength={150} value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})}/></label>
      <label>Företag eller restaurang<input maxLength={150} value={draft.business_name||""} onChange={e=>setDraft({...draft,business_name:e.target.value})}/></label>
      <label>Rabattkod<input maxLength={100} value={draft.discount_code||""} onChange={e=>setDraft({...draft,discount_code:e.target.value})}/></label>
      <label>Gäller till<input type="date" value={draft.valid_until||""} onChange={e=>setDraft({...draft,valid_until:e.target.value})}/></label>
      <label>Länk<input type="text" placeholder="exempel.se/erbjudande" value={draft.url||""} onChange={e=>setDraft({...draft,url:e.target.value})}/></label>
      <label>Visningsordning<input type="number" min={0} max={999} value={draft.sort_order} onChange={e=>setDraft({...draft,sort_order:Number(e.target.value)})}/></label>
      <label className="cn-partner-wide">Beskrivning och villkor<textarea maxLength={1500} value={draft.description||""} onChange={e=>setDraft({...draft,description:e.target.value})}/></label>
      <label className="cn-partner-check"><input type="checkbox" checked={draft.active} onChange={e=>setDraft({...draft,active:e.target.checked})}/> Visa i turneringsvyn</label>
    </div>
    <div className="cn-partner-actions"><button type="submit" disabled={busy}>{value?"Spara erbjudande":"Lägg till erbjudande"}</button>{value&&onDelete&&<button type="button" disabled={busy} onClick={()=>void onDelete(value)}>Ta bort</button>}</div>
  </form>;
}

export default function PartnersAdmin({token,cupId}:{token:string;cupId:number}) {
  const [data,setData]=useState<Partners|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");
  const load=useCallback(async()=>setData(await req<Partners>(`/api/admin/cups/${cupId}/partners`,token)),[cupId,token]);
  useEffect(()=>{setData(null);setError("");void load().catch(err=>setError(err instanceof Error?err.message:"Sponsorer kunde inte hämtas."));},[load]);
  async function mutate(path:string,options:RequestInit,done:string):Promise<boolean> {
    setBusy(true);setError("");setMessage("");
    try{await req(path,token,options);await load();setMessage(done);return true;}
    catch(err){setError(err instanceof Error?err.message:"Kunde inte spara.");return false;}
    finally{setBusy(false);}
  }
  async function saveSponsor(draft:typeof newSponsor,existing?:Sponsor) {
    return mutate(`/api/admin/cups/${cupId}/sponsors${existing?`/${existing.id}`:""}`,
      {method:existing?"PUT":"POST",body:JSON.stringify({...draft,expected:existing})},"Sponsorn är sparad.");
  }
  async function saveOffer(draft:typeof newOffer,existing?:Offer) {
    return mutate(`/api/admin/cups/${cupId}/offers${existing?`/${existing.id}`:""}`,
      {method:existing?"PUT":"POST",body:JSON.stringify({...draft,expected:existing})},"Erbjudandet är sparat.");
  }
  async function remove(kind:"sponsors"|"offers",item:Sponsor|Offer) {
    if(!window.confirm("Vill du ta bort posten permanent?"))return;
    await mutate(`/api/admin/cups/${cupId}/${kind}/${item.id}`,{method:"DELETE"},"Posten är borttagen.");
  }
  return <section className="admin-panel cn-partners-admin" id="partners">
    <div className="admin-panel__top"><span>VERKTYG / PARTNERS</span><strong>VALFRITT</strong></div>
    <h2>Sponsorer & erbjudanden</h2><p>Lägg till samarbeten som ska synas under Erbjudanden i den publika turneringsvyn. Dolda poster visas bara här.</p>
    {error&&<p className="cn-partner-error" role="alert">{error} <button type="button" onClick={()=>void load().catch(()=>{})}>Ladda om</button></p>}
    {message&&<p role="status">{message}</p>}
    {!data?<p>Hämtar partners…</p>:<>
      <h3>Sponsorer ({data.sponsors.length})</h3>
      <details className="cn-partner-editor"><summary>+ Lägg till sponsor</summary><SponsorEditor busy={busy} onSave={saveSponsor}/></details>
      {data.sponsors.map(item=><details className="cn-partner-editor" key={item.id}><summary>{item.active?"●":"○"} {item.name} {item.active?"":"· Dold"}</summary><SponsorEditor value={item} busy={busy} onSave={saveSponsor} onDelete={sponsor=>remove("sponsors",sponsor)}/></details>)}
      <h3>Erbjudanden ({data.offers.length})</h3>
      <details className="cn-partner-editor"><summary>+ Lägg till erbjudande</summary><OfferEditor busy={busy} onSave={saveOffer}/></details>
      {data.offers.map(item=><details className="cn-partner-editor" key={item.id}><summary>{item.active?"●":"○"} {item.title} {item.active?"":"· Dolt"}</summary><OfferEditor value={item} busy={busy} onSave={saveOffer} onDelete={offer=>remove("offers",offer)}/></details>)}
    </>}
  </section>;
}
