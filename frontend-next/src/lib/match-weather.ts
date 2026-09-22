/** Hourly forecasts shared by matches at the same place. No result polling here. */
export type WeatherHour = {temperature:number; code:number|null; rain:number|null; wind:number|null};
export type HourlyForecast = {status:"ready"; location:string; timezone:string; hours:Record<string,WeatherHour>} | {status:"missing"|"error"};
export type MatchWeather = {status:"ready"; hour:WeatherHour; location:string} | {status:"loading"|"too-early"|"missing"|"error"|"past"};
const CACHE_MS=30*60*1000;
const cache=new Map<string,{until:number;promise:Promise<HourlyForecast>}>();
const finite=(value:unknown):number|null=>typeof value==="number"&&Number.isFinite(value)?value:null;
const normalize=(value:string)=>value.trim().toLocaleLowerCase("sv-SE");

export function localHour(kickoff:string, timezone="Europe/Stockholm"):string|null {
  if(!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(kickoff))return null;
  // Offset-free database times are cup-local wall times, never viewer-local.
  if(!/(?:Z|[+-]\d{2}:?\d{2})$/.test(kickoff))return kickoff.replace(" ","T").slice(0,13)+":00";
  const date=new Date(kickoff);if(!Number.isFinite(date.getTime()))return null;
  const parts=new Intl.DateTimeFormat("sv-SE",{timeZone:timezone,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(date);
  const get=(type:string)=>parts.find(p=>p.type===type)?.value;
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:00`;
}

export function forecastAvailability(kickoff:string|null|undefined, now=Date.now()):"available"|"too-early"|"missing"|"past" {
  const hour=kickoff?localHour(kickoff):null;if(!hour)return "missing";
  const today=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Stockholm",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(now));
  const days=Math.round((Date.parse(hour.slice(0,10)+"T00:00:00Z")-Date.parse(today+"T00:00:00Z"))/86400000);
  if(!Number.isFinite(days))return "missing";
  return days>15?"too-early":days < -1?"past":"available";
}

export function weatherForKickoff(forecast:HourlyForecast|undefined,kickoff:string|null|undefined,now=Date.now()):MatchWeather {
  const status=forecastAvailability(kickoff,now);
  if(status!=="available")return {status};
  if(!forecast)return {status:"loading"};
  if(forecast.status!=="ready")return {status:forecast.status};
  const key=localHour(kickoff!,forecast.timezone);
  const hour=key?forecast.hours[key]:undefined;
  return hour?{status:"ready",hour,location:forecast.location}:{status:"missing"};
}

export function weatherDescription(code:number|null):string {
  if(code===null)return "Prognos";
  if(code===0)return "Klart";
  if(code<=3)return "Molnigt";
  if(code===45||code===48)return "Dimma";
  if([71,73,75,77,85,86].includes(code))return "Snö";
  if(code>=95)return "Åska";
  return "Regn";
}

export function parseHourlyForecast(data:unknown, location:string):HourlyForecast {
  const raw=data as {timezone?:string;hourly?:Record<string,unknown[]>};
  if(!raw?.hourly||!Array.isArray(raw.hourly.time))return {status:"error"};
  const timezone=raw.timezone||"Europe/Stockholm";
  try{new Intl.DateTimeFormat("sv-SE",{timeZone:timezone});}catch{return {status:"error"};}
  const hours:Record<string,WeatherHour>={};
  raw.hourly.time.forEach((time,i)=>{
    const temperature=finite(raw.hourly?.temperature_2m?.[i]);
    if(typeof time!=="string"||temperature===null)return;
    hours[time]={temperature,code:finite(raw.hourly?.weather_code?.[i]),rain:finite(raw.hourly?.precipitation_probability?.[i]),wind:finite(raw.hourly?.wind_speed_10m?.[i])};
  });
  return Object.keys(hours).length?{status:"ready",hours,location,timezone}:{status:"missing"};
}

export function loadHourlyForecast(address:string,now=Date.now(),fetcher:typeof fetch=fetch):Promise<HourlyForecast> {
  const key=normalize(address);
  if(!key)return Promise.resolve({status:"missing"});
  const existing=cache.get(key);if(existing&&existing.until>now)return existing.promise;
  const entry:{until:number;promise:Promise<HourlyForecast>}={until:now+CACHE_MS,promise:Promise.resolve({status:"missing"})};
  entry.promise=(async():Promise<HourlyForecast>=>{
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
    async function json(url:string|URL){const response=await fetcher(url,{signal:controller.signal});if(!response.ok)throw Error(`Weather ${response.status}`);return response.json();}
    try {
      // Search the saved location first; an explicitly supplied town after a
      // comma is an acceptable forecast area, displayed next to the forecast.
      const town=address.split(",").at(-1)!.trim().replace(/^\d{3}\s?\d{2}\s+/,"");
      const queries=[...new Set([address.trim(),town])].filter(Boolean);
      let place:{name:string;latitude:number;longitude:number;timezone?:string}|undefined;
      for(const query of queries){
        const geo=await json(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=5&language=sv&format=json`);
        const candidates=(Array.isArray(geo.results)?geo.results:[]).filter((p:{name?:string})=>normalize(p.name||"")===normalize(query));
        // Never silently select another town from an ambiguous/fuzzy match.
        if(candidates.length===1&&finite(candidates[0].latitude)!==null&&finite(candidates[0].longitude)!==null){place=candidates[0];break;}
      }
      if(!place)return {status:"missing"};
      const url=new URL("https://api.open-meteo.com/v1/forecast");
      url.search=new URLSearchParams({latitude:String(place.latitude),longitude:String(place.longitude),timezone:place.timezone||"Europe/Stockholm",forecast_days:"16",past_days:"1",wind_speed_unit:"ms",hourly:"temperature_2m,weather_code,precipitation_probability,wind_speed_10m"}).toString();
      return parseHourlyForecast(await json(url),place.name);
    }catch{entry.until=now+60000;return {status:"error"};}
    finally{clearTimeout(timeout);}
  })();
  if(cache.size>=32)cache.delete(cache.keys().next().value!);
  cache.set(key,entry);
  return entry.promise;
}
