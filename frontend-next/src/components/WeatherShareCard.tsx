"use client";

import { useEffect, useMemo, useState } from "react";

type Forecast = {
  date: string;
  max: number;
  min: number;
  rain: number;
  wind: number;
  code: number;
};

const weatherLabel = (code:number) => {
  if (code === 0) return "Klart";
  if (code <= 3) return "Molnigt";
  if (code <= 48) return "Dimma";
  if (code <= 67) return "Regn";
  if (code <= 77) return "Snö";
  if (code <= 82) return "Regnskurar";
  if (code <= 86) return "Snöbyar";
  return "Åska";
};

const fmtDate = (value:string) => {
  const d = new Date(`${value}T12:00:00`);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat("sv-SE", { weekday:"short", day:"numeric", month:"short" }).format(d);
};

export function WeatherShareCard({
  address,
  startDate,
  endDate,
  cupName,
}:{address?:string|null;startDate?:string|null;endDate?:string|null;cupName:string}){
  const [forecast,setForecast] = useState<Forecast[]>([]);
  const [weatherState,setWeatherState] = useState<"idle"|"loading"|"ready"|"too-early"|"missing"|"error">("idle");
  const [pageUrl,setPageUrl] = useState("");

  useEffect(()=>{ setPageUrl(window.location.href); },[]);

  useEffect(()=>{
    if(!address || !startDate){ setWeatherState("missing"); return; }
    const start = new Date(`${startDate.slice(0,10)}T12:00:00`).getTime();
    const daysAway = Math.floor((start-Date.now())/86400000);
    if(daysAway > 16){ setWeatherState("too-early"); return; }
    if(daysAway < -1){ setWeatherState("missing"); return; }

    let cancelled = false;
    const run = async()=>{
      try{
        setWeatherState("loading");
        const geo = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(address)}&count=1&language=sv&format=json`).then(r=>r.json());
        const place = geo?.results?.[0];
        if(!place) throw new Error("no-place");
        const finalEnd = (endDate || startDate).slice(0,10);
        const url = new URL("https://api.open-meteo.com/v1/forecast");
        url.searchParams.set("latitude", String(place.latitude));
        url.searchParams.set("longitude", String(place.longitude));
        url.searchParams.set("timezone", "auto");
        url.searchParams.set("start_date", startDate.slice(0,10));
        url.searchParams.set("end_date", finalEnd);
        url.searchParams.set("daily", "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max");
        const data = await fetch(url.toString()).then(r=>r.json());
        const daily = data?.daily;
        if(!daily?.time?.length) throw new Error("no-forecast");
        const rows:Forecast[] = daily.time.map((date:string,i:number)=>({
          date,
          code:Number(daily.weather_code?.[i] ?? 0),
          max:Number(daily.temperature_2m_max?.[i] ?? 0),
          min:Number(daily.temperature_2m_min?.[i] ?? 0),
          rain:Number(daily.precipitation_probability_max?.[i] ?? 0),
          wind:Number(daily.wind_speed_10m_max?.[i] ?? 0),
        }));
        if(!cancelled){ setForecast(rows); setWeatherState("ready"); }
      }catch{
        if(!cancelled) setWeatherState("error");
      }
    };
    run();
    return()=>{cancelled=true};
  },[address,startDate,endDate]);

  const qrSrc = useMemo(()=> pageUrl ? `https://quickchart.io/qr?text=${encodeURIComponent(pageUrl)}&size=220&margin=1&ecLevel=M` : "",[pageUrl]);

  return <>
    <article className="feature-card">
      <span className="feature-card__number">WEATHER//LIVE</span>
      <h3>Väder på cupdagen</h3>
      {weatherState==="loading"&&<p>Hämtar prognosen…</p>}
      {weatherState==="too-early"&&<p>Prognosen visas automatiskt när cupen är inom 16 dagar.</p>}
      {weatherState==="missing"&&<p>Väder visas när cupen har datum och en plats som går att hitta.</p>}
      {weatherState==="error"&&<p>Väderprognosen kunde inte hämtas just nu.</p>}
      {weatherState==="ready"&&<div>{forecast.slice(0,4).map(day=><div key={day.date} style={{display:"grid",gridTemplateColumns:"1fr auto",gap:"4px 14px",padding:"9px 0",borderTop:"1px solid rgba(16,38,48,.15)"}}><strong style={{textTransform:"capitalize"}}>{fmtDate(day.date)} · {weatherLabel(day.code)}</strong><strong>{Math.round(day.max)}° / {Math.round(day.min)}°</strong><span>Regnrisk {Math.round(day.rain)}%</span><span>Vind {Math.round(day.wind)} km/h</span></div>)}</div>}
      <p style={{fontSize:11,opacity:.7,marginTop:12}}>Prognosdata: Open-Meteo.</p>
    </article>

    <article className="feature-card">
      <span className="feature-card__number">SHARE//QR</span>
      <h3>Skanna och följ cupen</h3>
      <p>Öppna samma livevy direkt i mobilen. QR-koden pekar alltid på den här cupens sida.</p>
      {qrSrc&&<div style={{display:"inline-flex",padding:8,background:"#fff",border:"1.5px solid #17323e",borderRadius:12}}><img src={qrSrc} width="176" height="176" alt={`QR-kod till ${cupName}`} /></div>}
    </article>
  </>;
}
