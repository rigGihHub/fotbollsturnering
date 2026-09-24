import {MatchWeather as Forecast,weatherDescription} from "@/lib/match-weather";
import styles from "./match-weather.module.css";

export function MatchWeather({forecast}:{forecast?:Forecast}){
  if(!forecast||forecast.status==="past")return null;
  // A repeated placeholder on every future match makes the schedule much longer
  // without helping the visitor. Reserve the row for an actual forecast.
  if(forecast.status!=="ready")return null;
  const {hour,location}=forecast;
  return <div className={styles.forecast} aria-label={`Väderprognos vid avspark, ${location}`}>
    <span className={styles.label}>Vid avspark · {location}</span>
    <div className={styles.values}><strong>{Math.round(hour.temperature)}°</strong><span>{weatherDescription(hour.code)}</span>{hour.rain!==null&&<span>Regnrisk {Math.round(hour.rain)}%</span>}{hour.wind!==null&&<span>Vind {Math.round(hour.wind)} m/s</span>}</div>
    <a className={styles.source} href="https://open-meteo.com/" target="_blank" rel="noreferrer">Prognos: Open-Meteo</a>
  </div>;
}
