"use client";

import { useId } from "react";

const validColor=(value?:string|null,fallback="#2257d6")=>value&&/^#[0-9a-f]{6}$/i.test(value)?value:fallback;

export function TeamKit({primary,secondary,pattern}:{primary?:string|null;secondary?:string|null;pattern?:string|null}){
  const rawId=useId().replace(/:/g,"");
  const patternId=`kit-${rawId}`;
  const c1=validColor(primary);
  const c2=validColor(secondary,"#ffffff");
  const shirt="M18 8 27 3 35 8 45 8 53 3 62 8 76 15 69 29 61 25 61 69 19 69 19 25 11 29 4 15Z";
  const normalized=(pattern||"Helfärgad").toLocaleLowerCase("sv");
  const patterned=normalized!=="helfärgad";
  return <svg className="team-kit" viewBox="0 0 80 74" role="img" aria-label={`Fotbollströja, ${pattern||"helfärgad"}`}>
    <defs>
      <pattern id={patternId} width="16" height="16" patternUnits="userSpaceOnUse">
        {normalized.includes("vertikala")?<><rect width="8" height="16" fill={c1}/><rect x="8" width="8" height="16" fill={c2}/></>
        :normalized.includes("horisontella")?<><rect width="16" height="8" fill={c1}/><rect y="8" width="16" height="8" fill={c2}/></>
        :normalized.includes("rutig")?<><rect width="16" height="16" fill={c1}/><rect x="8" width="8" height="8" fill={c2}/><rect y="8" width="8" height="8" fill={c2}/></>
        :normalized.includes("diagonala")?<><rect width="16" height="16" fill={c1}/><path d="M-4 12 12-4M4 20 20 4" stroke={c2} strokeWidth="6"/></>
        :normalized.includes("grafiskt")?<><rect width="16" height="16" fill={c1}/><path d="M0 5 16 0v7L0 12Z" fill={c2}/></>
        :<><rect width="8" height="16" fill={c1}/><rect x="8" width="8" height="16" fill={c2}/></>}
      </pattern>
      <linearGradient id={`${patternId}-shine`} x1="0" x2="1"><stop stopColor="#fff" stopOpacity=".32"/><stop offset=".38" stopColor="#fff" stopOpacity="0"/><stop offset="1" stopColor="#07131b" stopOpacity=".18"/></linearGradient>
    </defs>
    <path d={shirt} fill={patterned?`url(#${patternId})`:c1} stroke="#101f2a" strokeWidth="2.5" strokeLinejoin="round"/>
    <path d={shirt} fill={`url(#${patternId}-shine)`}/>
    <path d="M31 6 Q40 17 49 6" fill="none" stroke="#101f2a" strokeWidth="2.2"/>
    <path d="M20 67H60" stroke="#101f2a" strokeOpacity=".35"/>
  </svg>;
}
