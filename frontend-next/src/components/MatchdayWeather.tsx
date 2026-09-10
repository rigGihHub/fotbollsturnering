"use client";

import { useEffect, useMemo, useState } from "react";

type MatchdayForecast = {
  time: string;
  temperature: number;
  rain: number;
  wind: number;
  code: number;
};

type WeatherState = "idle"|"loading"|"ready"|"too-early"|"missing"|"error";

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

const hourLabel = (value:string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "vid matchstart";
  return new Intl.DateTimeFormat("sv-SE", { hour:"2-digit", minute:"2-digit" }).format(parsed);
};

export function MatchdayWeather({address,matchStart}:{address?:string|null;matchStart?:string|null}){
  const [forecast,setForecast] = useState<MatchdayForecast|null>(null);
  const [weatherState,setWeatherState] = useState<WeatherState>("idle");

  const matchTimestamp = useMemo(()=>{
    const value = matchStart ? new Date(matchStart).getTime() : NaN;
    return Number.isFinite(value) ? value : null;
  },[matchStart]);

  useEffect(()=>{
    if(!address || !matchStart || matchTimestamp===null){ setForecast(null); setWeatherState("missing"); return; }
    const daysAway = Math.floor((matchTimestamp-Date.now())/86400000);
    if(daysAway > 16){ setForecast(null); setWeatherState("too-early"); return; }
    if(daysAway < -1){ setForecast(null); setWeatherState("missing"); return; }

    let cancelled = false;
    const run = async()=>{
      try{
        setWeatherState("loading");
        const geoResponse = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(address)}&count=1&language=sv&format=json`);
        if(!geoResponse.ok) throw new Error("geocoding-failed");
        const geo = await geoResponse.json();
        const place = geo?.results?.[0];
        if(!place) throw new Error("no-place");

        const date = matchStart.slice(0,10);
        const url = new URL("https://api.open-meteo.com/v1/forecast");
        url.searchParams.set("latitude", String(place.latitude));
        url.searchParams.set("longitude", String(place.longitude));
        url.searchParams.set("timezone", "auto");
        url.searchParams.set("start_date", date);
        url.searchParams.set("end_date", date);
        url.searchParams.set("hourly", "temperature_2m,precipitation_probability,wind_speed_10m,weather_code");
        const response = await fetch(url.toString());
        if(!response.ok) throw new Error("forecast-failed");
        const data = await response.json();
        const hourly = data?.hourly;
        if(!hourly?.time?.length) throw new Error("no-forecast");

        const index = hourly.time.reduce((best:number,current:string,i:number)=>{
          const currentDistance = Math.abs(new Date(current).getTime()-matchTimestamp);
          const bestDistance = Math.abs(new Date(hourly.time[best]).getTime()-matchTimestamp);
          return currentDistance < bestDistance ? i : best;
        },0);
        const temperature = Number(hourly.temperature_2m?.[index]);
        const rain = Number(hourly.precipitation_probability?.[index]);
        const wind = Number(hourly.wind_speed_10m?.[index]);
        const code = Number(hourly.weather_code?.[index]);
        if(![temperature,rain,wind,code].every(Number.isFinite)) throw new Error("incomplete-forecast");

        if(!cancelled){
          setForecast({time:hourly.time[index],temperature,rain,wind,code});
          setWeatherState("ready");
        }
      }catch{
        if(!cancelled){ setForecast(null); setWeatherState("error"); }
      }
    };
    run();
    return()=>{cancelled=true};
  },[address,matchStart,matchTimestamp]);

  return <div className="matchday-weather" aria-live="polite">
    <div className="matchday-weather__label"><span>WEATHER//NEXT</span><strong>Vid nästa match</strong></div>
    {weatherState==="loading"&&<p>Hämtar vädret vid matchstart…</p>}
    {weatherState==="too-early"&&<p>Prognosen visas här när nästa match är inom 16 dagar.</p>}
    {weatherState==="missing"&&<p>Väder visas när nästa match har tid och cupen har en sökbar plats.</p>}
    {weatherState==="error"&&<p>Vädret vid nästa match kunde inte hämtas just nu.</p>}
    {weatherState==="ready"&&forecast&&<div className="matchday-weather__data">
      <div><strong>{Math.round(forecast.temperature)}°</strong><span>{weatherLabel(forecast.code)} · ca {hourLabel(forecast.time)}</span></div>
      <div><strong>{Math.round(forecast.rain)}%</strong><span>regnrisk</span></div>
      <div><strong>{Math.round(forecast.wind)}</strong><span>km/h vind</span></div>
    </div>}
    <small>Prognosdata: Open-Meteo.</small>
  </div>;
}
