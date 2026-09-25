"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CLIENT_API_BASE } from "../lib/client-api";
import MatchEventsAdmin from "./match-events-admin";

const API = CLIENT_API_BASE;

async function req(path:string,token:string,init:RequestInit={}) {
  const headers=new Headers(init.headers);
  headers.set("Authorization",`Bearer ${token}`);
  if(init.body)headers.set("Content-Type","application/json");
  const response=await fetch(`${API}${path}`,{...init,headers,cache:"no-store"});
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(payload?.detail||`API-fel ${response.status}`);
  return payload;
}

type Mode="publish"|"reporting";
type Match={requires_winner?:boolean;id:number;stage?:string|null;home_team:string;away_team:string;home_score:number|null;away_score:number|null;home_penalties?:number|null;away_penalties?:number|null;status:string;match_status?:string|null;scheduled_start?:string|null};
type ScheduleConflict={type:string;severity:"error"|"warning";message:string;match_ids?:number[]};
type PublicationPayload={tournament?:{is_published?:boolean};ready:boolean;blockers:string[];import_context?:{playoff_imported?:boolean;rules_imported?:boolean;schedule_imported?:boolean;pitch_windows_imported?:boolean;source_name?:string|null};schedule_conflict_analysis?:{error_count:number;warning_count:number;conflicts:ScheduleConflict[]}};
type Impact={playoff:boolean;outcome_changes:boolean;blocked:boolean;downstream_count?:number;summary?:string;guidance?:string[];downstream?:Array<{id:number;stage?:string|null;match_no?:number|null;scheduled_start?:string|null;locked:boolean;recoverable:boolean;recovery_reason:string}>};

function compactRows(rows:string[]) {
  const counts=new Map<string,number>();
  for(const row of rows){const text=String(row||"").trim();if(text)counts.set(text,(counts.get(text)||0)+1);}
  return [...counts].map(([text,count])=>({text,count}));
}

function blockerGuide(text:string, imported?:PublicationPayload["import_context"]){
  const lower=text.toLocaleLowerCase("sv-SE");
  if(lower.includes("slutspelsmodell")||lower.includes("cupregler")){
    return imported?.playoff_imported
      ? {where:"Slutspel",target:"#playoffs",action:"Kontrollera den importerade modellen och tryck ”Spara slutspelsregler”. Uppgifterna finns redan i cupen; sparningen bekräftar att upplägget är rätt."}
      : {where:"Slutspel",target:"#playoffs",action:"Öppna Slutspel, välj modell och regel vid oavgjort och tryck ”Spara slutspelsregler”."};
  }
  if(lower.includes("schemat behöver kontrolleras"))return {where:"Schema",target:"#schedule",action:"Öppna Schema, kontrollera tider och planer och tryck ”Godkänn schemat”. Importerade matcher behöver ändå godkännas efter en ändring av regler eller plantider."};
  if(lower.includes("schema saknas"))return {where:"Schema",target:"#schedule",action:"Öppna Schema och skapa eller importera matchprogrammet."};
  if(lower.includes("spelplats")||lower.includes("adress"))return {where:"Cupinfo",target:"#cupinfo",action:"Öppna Cupinfo och fyll i spelplats eller adress. Om importen redan hittade platsen ska den bara kontrolleras och sparas."};
  if(lower.includes("slutspelsträdet"))return {where:"Slutspel",target:"#playoffs",action:"Öppna Slutspel och rätta den markerade källan eller matchen."};
  return {where:"Kontroll & publicering",action:"Öppna det angivna steget och åtgärda felet där."};
}

function compactConflicts(rows:ScheduleConflict[]) {
  const counts=new Map<string,{item:ScheduleConflict;count:number}>();
  for(const item of rows){const key=`${item.type}:${item.message}`;const current=counts.get(key);counts.set(key,{item,count:(current?.count||0)+1});}
  return [...counts.values()];
}

export default function PublishReportingAdmin({token,cupId,mode,publicSlug}:{token:string;cupId:number;mode:Mode;publicSlug?:string|null}) {
  const [publication,setPublication]=useState<PublicationPayload|null>(null);
  const [matches,setMatches]=useState<Match[]>([]);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

  const load=useCallback(async()=>{
    try{
      if(mode==="publish")setPublication(await req(`/api/admin/cups/${cupId}/publication`,token));
      else {const data=await req(`/api/admin/cups/${cupId}/reporting`,token);setMatches(data.matches||[]);}
      setError("");
    }catch(reason){setError(reason instanceof Error?reason.message:"Kunde inte hämta data");}
  },[token,cupId,mode]);

  useEffect(()=>{void load();},[load]);

  async function togglePublication(){
    setBusy(true);
    try{
      setError("");
      setPublication(await req(`/api/admin/cups/${cupId}/publication`,token,{method:"PUT",body:JSON.stringify({published:!publication?.tournament?.is_published})}));
    }catch(reason){setError(reason instanceof Error?reason.message:"Publicering misslyckades");}
    finally{setBusy(false);}
  }

  async function save(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string){
    setBusy(true);
    try{
      setError("");
      const payload={home_score:Number(home),away_score:Number(away),home_penalties:homePenalties===""?null:Number(homePenalties),away_penalties:awayPenalties===""?null:Number(awayPenalties),expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null};
      if((match.requires_winner??(match.stage!=="Gruppspel"))&&(match.home_score!=null||match.away_score!=null)){
        const impact=await req(`/api/admin/cups/${cupId}/reporting/matches/${match.id}/impact`,token,{method:"POST",body:JSON.stringify(payload)}) as Impact;
        if(impact.blocked){const details=(impact.guidance||[]).join(" ");throw new Error(`${impact.summary||"Korrigeringen påverkar en senare slutspelsmatch."}${details?` ${details}`:""}`);}
        if(impact.outcome_changes&&(impact.downstream_count||0)>0){
          const rows=(impact.downstream||[]).map(item=>`${item.stage||"Slutspel"}${item.match_no?` #${item.match_no}`:""}${item.locked?" · låst":" · ej startad"}`).join("\n");
          if(!window.confirm(`Korrigeringen ändrar hela kedjeeffekten för vilket lag som går vidare och påverkar ${impact.downstream_count} senare match${impact.downstream_count===1?"":"er"}.\n\n${rows}\n\nVill du fortsätta?`))return;
        }
      }
      await req(`/api/admin/cups/${cupId}/reporting/matches/${match.id}`,token,{method:"PUT",body:JSON.stringify(payload)});
      await load();
    }catch(reason){setError(reason instanceof Error?reason.message:"Resultatet kunde inte sparas");}
    finally{setBusy(false);}
  }

  async function reset(match:Match){
    if(match.home_score==null||match.away_score==null)return;
    if(!window.confirm(`Återställ ${match.home_team} – ${match.away_team} som ospelad?\n\nResultatet, matchstatusen, matchklockan och registrerade matchhändelser tas bort.`))return;
    setBusy(true);
    try{
      setError("");
      await req(`/api/admin/cups/${cupId}/reporting/matches/${match.id}/reset`,token,{method:"POST",body:JSON.stringify({expected_home_score:match.home_score,expected_away_score:match.away_score,expected_home_penalties:match.home_penalties??null,expected_away_penalties:match.away_penalties??null,expected_status:match.match_status||"not_started"})});
      await load();
    }catch(reason){setError(reason instanceof Error?reason.message:"Matchen kunde inte återställas");}
    finally{setBusy(false);}
  }

  const blockers=publication?.blockers??[];
  const scheduleErrors=publication?.schedule_conflict_analysis?.conflicts?.filter(item=>item.severity==="error")||[];
  const otherBlockers=useMemo(()=>compactRows(blockers).filter(({text})=>!(scheduleErrors.length&&/schemafel/i.test(text))),[blockers,scheduleErrors.length]);
  const conflictGroups=useMemo(()=>compactConflicts(scheduleErrors),[scheduleErrors]);
  const played=matches.filter(match=>match.status==="played").length;
  const awaiting=matches.filter(match=>match.status==="awaiting_decision").length;

  if(mode==="publish"){
    if(!publication&&!error)return <section className="admin-panel publication-console publication-console--loading" id="publish" aria-live="polite"><div className="publication-console__eyebrow"><span>07 · KONTROLL & PUBLICERING</span><strong>KONTROLLERAR</strong></div><div className="publication-console__hero"><span className="publication-console__signal" aria-hidden="true">…</span><div><p className="publication-console__kicker">Slutkontroll</p><h2>Kontrollerar cupen</h2><p>CupNavi hämtar aktuell cupdata och letar efter sådant som måste rättas före publicering.</p></div></div></section>;
    const isLive=Boolean(publication?.tournament?.is_published);
    const isReady=Boolean(publication?.ready);
    const issueCount=otherBlockers.reduce((sum,item)=>sum+item.count,0)+scheduleErrors.length;
    return <section className={`admin-panel publication-console ${isReady?"is-ready":"needs-action"}`} id="publish">
      <div className="publication-console__eyebrow"><span>07 · KONTROLL & PUBLICERING</span><strong>{isLive?"LIVE":"UTKAST"}</strong></div>
      <div className="publication-console__hero">
        <span className="publication-console__signal" aria-hidden="true">{isReady?"✓":"!"}</span>
        <div><p className="publication-console__kicker">{isReady?"Redo för publik":"Åtgärder krävs"}</p><h2>{isLive?"Cupen är publicerad":isReady?"Allt är klart":"Inte redo att publicera"}</h2><p>{isReady?"Kontrollerna är godkända. Du kan publicera cupen när du vill.":`${issueCount} ${issueCount===1?"sak behöver":"saker behöver"} rättas innan cupen kan bli publik.`}</p></div>
      </div>
      {error&&<div className="publication-console__error" role="alert"><strong>Något gick fel</strong><span>{error}</span></div>}
      {!isReady&&<div className="publication-checklist">
        <div className="publication-checklist__head"><div><span>CHECKLISTA</span><strong>Gör detta före publicering</strong></div><b>{issueCount}</b></div>
        {otherBlockers.map(({text,count})=>{const guide=blockerGuide(text,publication?.import_context);return <div className="publication-checklist__item" key={text}><span className="publication-checklist__icon">!</span><div><strong>{text}</strong><small><b>Var:</b> {guide.where}. {guide.action}{guide.target&&<> <a href={guide.target}>Öppna steget →</a></>}</small></div>{count>1&&<b>×{count}</b>}</div>})}
        {conflictGroups.map(({item,count})=><div className="publication-checklist__item is-blocking" key={`${item.type}:${item.message}`}><span className="publication-checklist__icon">!</span><div><strong>{item.message}</strong><small><b>Var:</b> Schema. {item.type==="round_order"?"Rätta rondordningen och godkänn sedan schemat.":"Öppna Schema, rätta konflikten och godkänn sedan schemat."}</small></div>{count>1&&<b>×{count}</b>}</div>)}
      </div>}
      {isReady&&<div className="publication-ready-steps"><div><b>1</b><span><strong>Kontrollera sammanfattningen</strong><small>CupNavi har inte hittat några blockerande fel.</small></span></div><div><b>2</b><span><strong>Förhandsgranska cupvyn</strong><small>Kontrollera hur tider, planer och lag visas för besökare.</small></span></div><div><b>3</b><span><strong>Publicera cupen</strong><small>Den publika länken blir tillgänglig för deltagarna.</small></span></div></div>}
      <div className="publication-console__actions">
        <span>{isLive?"Ändringar visas direkt i turneringsvyn.":isReady?"En sista kontroll görs när du publicerar.":"Publiceringsknappen aktiveras när checklistan är klar."}</span>
        <div>{otherBlockers.some(({text})=>/slutspelsmodell|cupregler/i.test(text))&&<a className="admin-action-secondary" href="#playoffs">Öppna Slutspel</a>}{otherBlockers.some(({text})=>/schema behöver|schema saknas|schemat behöver/i.test(text))||scheduleErrors.length>0?<a className="admin-action-secondary" href="#schedule">Öppna Schema</a>:null}{otherBlockers.some(({text})=>/spelplats|adress/i.test(text))&&<a className="admin-action-secondary" href="#cupinfo">Öppna Cupinfo</a>}{publicSlug&&<a className="admin-action-secondary" href={`/cup/${publicSlug}?preview=1&cup=${cupId}`} target="_blank" rel="noreferrer">Förhandsgranska</a>}<button className="admin-action-primary" disabled={busy||(!isLive&&!isReady)} onClick={togglePublication}>{busy?"Arbetar…":isLive?"Avpublicera":"Publicera cup"}</button></div>
      </div>
    </section>;
  }

  return <>
    <section className="admin-panel reporting-console" id="reporting">
      <div className="publication-console__eyebrow"><span>VERKTYG · MATCHRAPPORTERING</span><strong>{played}/{matches.length} KLARA</strong></div>
      <div className="reporting-console__head"><div><p className="publication-console__kicker">MATCHCENTRAL</p><h2>Rapportera resultat</h2><p>Välj en match, fyll i resultatet och spara. Admin kan korrigera även slutmarkerade matcher; rapportörsvyn låses efter slutmarkering.</p></div>{awaiting>0&&<span className="reporting-console__waiting">{awaiting} väntar på avgörande</span>}</div>
      {error&&<div className="publication-console__error" role="alert"><strong>Kunde inte spara</strong><span>{error}</span></div>}
      <div className="reporting-match-list">{matches.length?matches.map(match=><MatchRow key={match.id} match={match} busy={busy} save={save} reset={reset}/>):<div className="reporting-empty"><strong>Inga matcher att rapportera</strong><span>Matcher visas här när schemat är skapat.</span></div>}</div>
    </section>
    <MatchEventsAdmin token={token} cupId={cupId}/>
  </>;
}

function MatchRow({match,busy,save,reset}:{match:Match;busy:boolean;save:(match:Match,home:string,away:string,homePenalties:string,awayPenalties:string)=>void;reset:(match:Match)=>void}){
  const [home,setHome]=useState(match.home_score==null?"":String(match.home_score));
  const [away,setAway]=useState(match.away_score==null?"":String(match.away_score));
  const [homePenalties,setHomePenalties]=useState(match.home_penalties==null?"":String(match.home_penalties));
  const [awayPenalties,setAwayPenalties]=useState(match.away_penalties==null?"":String(match.away_penalties));
  useEffect(()=>{setHome(match.home_score==null?"":String(match.home_score));setAway(match.away_score==null?"":String(match.away_score));setHomePenalties(match.home_penalties==null?"":String(match.home_penalties));setAwayPenalties(match.away_penalties==null?"":String(match.away_penalties));},[match.home_score,match.away_score,match.home_penalties,match.away_penalties]);
  const knockout=(match.requires_winner??(match.stage!=="Gruppspel"));
  const tied=knockout&&home!==""&&away!==""&&Number(home)===Number(away);
  return <article className="reporting-match">
    <div className="reporting-match__meta"><span>{match.stage||"Match"}</span><small>{match.scheduled_start||"Ej schemalagd"}</small></div>
    <div className="reporting-match__teams"><strong>{match.home_team}</strong><span>–</span><strong>{match.away_team}</strong></div>
    <div className="reporting-match__score"><input aria-label="Hemmamål" type="number" min="0" value={home} onChange={event=>setHome(event.target.value)}/><span>–</span><input aria-label="Bortamål" type="number" min="0" value={away} onChange={event=>setAway(event.target.value)}/><button disabled={busy||home===""||away===""||(tied&&(homePenalties===""||awayPenalties===""))} onClick={()=>save(match,home,away,homePenalties,awayPenalties)}>{knockout&&match.home_score!=null?"Kontrollera & spara":"Spara"}</button>{match.home_score!=null&&match.away_score!=null&&<button className="reporting-match__reset" type="button" disabled={busy} onClick={()=>reset(match)}>Återställ som ospelad</button>}</div>
    {tied&&<div className="reporting-match__penalties"><span>Avgörande på straffar</span><label>{match.home_team}<input aria-label="Hemmastraffar" type="number" min="0" value={homePenalties} onChange={event=>setHomePenalties(event.target.value)}/></label><label>{match.away_team}<input aria-label="Bortastraffar" type="number" min="0" value={awayPenalties} onChange={event=>setAwayPenalties(event.target.value)}/></label></div>}
  </article>;
}
