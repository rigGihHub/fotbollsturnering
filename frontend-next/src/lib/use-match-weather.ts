"use client";
import {useEffect,useState} from "react";
import {Match,Pitch} from "./types";
import {forecastAvailability,HourlyForecast,loadHourlyForecast,MatchWeather,weatherForKickoff} from "./match-weather";

export function useMatchWeather(enabled:boolean,matches:Match[],pitches:Pitch[],address?:string|null) {
  const location=(match:Match)=>pitches.find(p=>p.pitch_number===Number(match.pitch_number))?.address?.trim()||address?.trim()||"";
  const requestKey=JSON.stringify(matches.map(m=>[location(m),m.scheduled_start]));
  const [state,setState]=useState<{key:string;forecasts:Record<string,HourlyForecast>;now:number}>({key:"",forecasts:{},now:0});
  useEffect(()=>{
    if(!enabled)return;
    const rows=JSON.parse(requestKey) as [string,string|null][];
    let cancelled=false,pending=false;let timer:ReturnType<typeof setTimeout>|undefined;
    async function refresh(){
      clearTimeout(timer);
      if(cancelled||pending||document.hidden)return;
      if(navigator.onLine===false){
        setState({key:requestKey,forecasts:Object.fromEntries(rows.map(([place])=>[place,{status:"error"} as HourlyForecast])),now:Date.now()});
        return;
      }
      pending=true;const now=Date.now();
      const addresses=[...new Set(rows.filter(([place,kickoff])=>place&&forecastAvailability(kickoff,now)==="available").map(([place])=>place))];
      const pairs=await Promise.all(addresses.map(async place=>[place,await loadHourlyForecast(place,now)] as const));
      pending=false;
      if(cancelled)return;
      setState({key:requestKey,forecasts:Object.fromEntries(pairs),now});
      if(!document.hidden)timer=setTimeout(refresh,pairs.some(([,f])=>f.status==="error")?60000:30*60*1000);
    }
    const visibility=()=>{clearTimeout(timer);if(!document.hidden)void refresh();};
    void refresh();document.addEventListener("visibilitychange",visibility);window.addEventListener("online",visibility);window.addEventListener("offline",visibility);
    return()=>{cancelled=true;clearTimeout(timer);document.removeEventListener("visibilitychange",visibility);window.removeEventListener("online",visibility);window.removeEventListener("offline",visibility);};
  },[enabled,requestKey]);
  return (match:Match):MatchWeather|undefined=>{
    if(!enabled||!match.scheduled_start)return undefined;
    if(!location(match))return {status:"missing"};
    if(state.key!==requestKey)return {status:"loading"};
    return weatherForKickoff(state.forecasts[location(match)],match.scheduled_start,state.now);
  };
}
