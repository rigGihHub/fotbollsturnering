const state={cup:null,page:"matches",teamId:null,cupKey:null,standings:null,playoffs:null,teamSummary:null};
const qs=new URLSearchParams(location.search);
const API_BASE=(window.CUPNAVI_API_BASE||"").replace(/\/$/,"");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const sourceTeam=s=>String(s||"").startsWith("team:")?Number(String(s).split(":")[1]):null;
const teamName=id=>state.cup?.teams.find(t=>Number(t.id)===Number(id))?.name||"TBD";
const srcLabel=s=>{const id=sourceTeam(s);return id?teamName(id):String(s||"TBD").replaceAll(":"," ");};

async function loadCup(key){
  const res=await fetch(`${API_BASE}/api/public/cups/${encodeURIComponent(key)}`);
  if(!res.ok) throw new Error("Cupen kunde inte hämtas.");
  state.cup=await res.json();
  state.cupKey=key;
  state.standings=null; state.playoffs=null; state.teamSummary=null;
  localStorage.setItem("cupnavi:lastCup",key);
  document.querySelector("#cupName").textContent=state.cup.tournament.name||"CupNavi";
  document.querySelector("#setup").classList.add("hidden");
  document.querySelector("#teamPicker").classList.remove("hidden");
  document.querySelector("#nav").classList.remove("hidden");
  const select=document.querySelector("#teamSelect");
  select.innerHTML=`<option value="">Alla lag</option>`+state.cup.teams.map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join("");
  const saved=localStorage.getItem(`cupnavi:team:${key}`);
  if(saved){state.teamId=Number(saved);select.value=saved;}
  render();
}
function relevant(matches){return state.teamId?matches.filter(m=>[sourceTeam(m.home_source),sourceTeam(m.away_source)].includes(state.teamId)):matches;}
function matchDate(m){const d=new Date(m.scheduled_start);return Number.isNaN(d.getTime())?null:d}
function pitchPoint(pitchNo){
  return (state.cup?.venue_points||[]).find(p=>p.kind==="Plan"&&(String(p.label).toLowerCase()===`plan ${pitchNo}`.toLowerCase()||String(p.label).endsWith(String(pitchNo))));
}
function renderLiveCenter(){
  if(!state.cup)return;
  const now=Date.now();
  const unplayed=state.cup.matches.filter(m=>m.home_score==null&&m.away_score==null);
  const live=unplayed.filter(m=>{const d=matchDate(m);return d&&d.getTime()<=now&&now<=d.getTime()+90*60*1000}).slice(0,4);
  const next=unplayed.filter(m=>{const d=matchDate(m);return d&&d.getTime()>now}).slice(0,3);
  const rows=live.length?live:next;
  const box=document.querySelector("#liveCenter");
  if(!rows.length){box.classList.add("hidden");box.innerHTML="";return}
  box.classList.remove("hidden");
  box.innerHTML=`<div class="live-center"><div class="live-title">${live.length?"🔴 Pågår nu":"⏱️ Nästa matcher"}</div>${rows.map(m=>`<div class="live-item"><span class="badge ${live.includes(m)?"live":""}">${live.includes(m)?"PÅGÅR":new Date(m.scheduled_start).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}</span><strong>${esc(srcLabel(m.home_source))} – ${esc(srcLabel(m.away_source))}</strong><span class="live-pitch">Plan ${esc(m.pitch_number)}</span></div>`).join("")}</div>`;
}
function renderMatches(){
  const rows=relevant(state.cup.matches);
  const now=Date.now();
  const next=rows.find(m=>m.home_score==null&&matchDate(m)&&matchDate(m).getTime()>=now);
  let html="";
  if(next){
    const point=pitchPoint(next.pitch_number);
    html+=`<div class="card next"><span class="badge">Nästa match</span><h2>${esc(srcLabel(next.home_source))} – ${esc(srcLabel(next.away_source))}</h2><div class="muted">${new Date(next.scheduled_start).toLocaleString()} · Plan ${esc(next.pitch_number)}</div>${point?.url?`<a class="venue-link" href="${esc(point.url)}" target="_blank" rel="noopener">📍 Vägbeskrivning</a>`:""}</div>`;
  }
  html+=rows.map(m=>`<div class="card match-card"><div class="row"><strong>${esc(srcLabel(m.home_source))} – ${esc(srcLabel(m.away_source))}</strong><span class="score">${m.home_score==null?"–":`${m.home_score}–${m.away_score}`}</span></div><div class="meta">${new Date(m.scheduled_start).toLocaleString()} · Plan ${esc(m.pitch_number)} · ${esc(m.stage)}</div></div>`).join("");
  return html||`<div class="card">Inga matcher att visa.</div>`;
}
async function fetchStandings(){
  if(!state.standings){
    const res=await fetch(`${API_BASE}/api/public/cups/${encodeURIComponent(state.cupKey)}/standings`);
    if(!res.ok) throw new Error("Tabellen kunde inte hämtas.");
    state.standings=await res.json();
  }
  return state.standings;
}
async function fetchPlayoffs(){
  if(!state.playoffs){
    const res=await fetch(`${API_BASE}/api/public/cups/${encodeURIComponent(state.cupKey)}/playoffs`);
    if(!res.ok) throw new Error("Slutspelet kunde inte hämtas.");
    state.playoffs=await res.json();
  }
  return state.playoffs;
}
async function fetchTeamSummary(){
  if(!state.teamId){state.teamSummary=null;return null;}
  const res=await fetch(`${API_BASE}/api/public/cups/${encodeURIComponent(state.cupKey)}/teams/${state.teamId}/summary`);
  if(!res.ok) throw new Error("Lagöversikten kunde inte hämtas.");
  state.teamSummary=await res.json();
  return state.teamSummary;
}
async function renderTable(){
  const payload=await fetchStandings();
  const groups=payload.groups||[];
  return groups.map(g=>`<div class="card"><h2>${esc(g.group.name)}</h2><div class="table-wrap"><table><thead><tr><th>#</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th><th>MS</th><th>P</th></tr></thead><tbody>${g.rows.map(r=>`<tr class="${state.teamId===Number(r.team_id)?"mine":""}"><td>${r.position}</td><td>${esc(r.Lag)}</td><td>${r.S}</td><td>${r.V}</td><td>${r.O}</td><td>${r.F}</td><td>${r.MS}</td><td><strong>${r.P}</strong></td></tr>`).join("")}</tbody></table></div></div>`).join("")||`<div class="card">Ingen tabelldata ännu.</div>`;
}
async function renderPlayoff(){
  const payload=await fetchPlayoffs();
  const brackets=payload.brackets||[];
  return brackets.map(b=>`<div class="card"><h2>${esc(b.name)}</h2>${b.matches.map(m=>`<div class="playoff-match"><span class="badge">${esc(m.stage)}</span><div class="row"><strong>${esc(srcLabel(m.home_source))} – ${esc(srcLabel(m.away_source))}</strong><strong>${m.home_score==null?"–":`${m.home_score}–${m.away_score}`}</strong></div><div class="muted">${m.scheduled_start?new Date(m.scheduled_start).toLocaleString():"Tid ej publicerad"}${m.pitch_number?` · Plan ${esc(m.pitch_number)}`:""}</div></div>`).join("")}</div>`).join("")||`<div class="card">Inget publicerat slutspel ännu.</div>`;
}
function renderInfo(){
  const t=state.cup.tournament||{};
  const points=state.cup.venue_points||[];
  let html="";
  if(t.public_information) html+=`<div class="card"><h2>Information från arrangören</h2><p>${esc(t.public_information)}</p></div>`;
  if(t.arena_address||t.kiosk_information||t.organizer_phone||t.feedback_email){
    html+=`<div class="card"><h2>Praktisk information</h2>${t.arena_address?`<p>📍 ${esc(t.arena_address)}</p>`:""}${t.kiosk_information?`<p>☕ ${esc(t.kiosk_information)}</p>`:""}${t.organizer_phone?`<p>📞 <a href="tel:${esc(t.organizer_phone)}">${esc(t.organizer_phone)}</a></p>`:""}${t.feedback_email?`<p>✉️ <a href="mailto:${esc(t.feedback_email)}">${esc(t.feedback_email)}</a></p>`:""}</div>`;
  }
  html+=points.map(p=>`<div class="card"><strong>📍 ${esc(p.label)}</strong><div class="muted">${esc(p.detail||"")}</div>${p.url?`<a class="venue-link" href="${esc(p.url)}" target="_blank" rel="noopener">Vägbeskrivning</a>`:""}</div>`).join("");
  return html||`<div class="card">Ingen publik information publicerad ännu.</div>`;
}
async function render(){
  if(!state.cup)return;
  renderLiveCenter();
  document.querySelectorAll("nav button").forEach(b=>b.classList.toggle("active",b.dataset.page===state.page));
  const view=document.querySelector("#view");
  view.innerHTML=`<div class="card muted">Laddar…</div>`;
  try{
    let teamHero="";
    if(state.teamId){
      const data=await fetchTeamSummary();
      const s=data?.summary;
      if(s){
        const nm=s.next_match;
        teamHero=`<div class="card next"><span class="badge">⭐ Mitt lag</span><h2>${esc(data.team.name)}</h2><div class="team-facts"><span>📊 ${s.group_position?`${s.group_position}:a`:"–"}</span><span>✅ ${s.played}/${s.matches} spelade</span>${s.next_playoff_match?`<span>🏆 ${esc(s.next_playoff_match.stage)}</span>`:""}</div>${nm?`<p><strong>Nästa:</strong> ${esc(srcLabel(nm.home_source))} – ${esc(srcLabel(nm.away_source))}<br><span class="muted">${new Date(nm.scheduled_start).toLocaleString()} · Plan ${esc(nm.pitch_number)}</span></p>`:""}</div>`;
      }
    }
    const content=state.page==="matches"?renderMatches():state.page==="table"?await renderTable():state.page==="playoff"?await renderPlayoff():renderInfo();
    view.innerHTML=teamHero+content;
  }catch(e){
    view.innerHTML=`<div class="card">${esc(e.message||"Något gick fel.")}</div>`;
  }
}
document.querySelector("#loadCup").onclick=async()=>{try{await loadCup(document.querySelector("#cupKey").value.trim())}catch(e){alert(e.message)}};
document.querySelector("#teamSelect").onchange=e=>{state.teamId=e.target.value?Number(e.target.value):null;state.teamSummary=null;const key=localStorage.getItem("cupnavi:lastCup");if(state.teamId)localStorage.setItem(`cupnavi:team:${key}`,state.teamId);else localStorage.removeItem(`cupnavi:team:${key}`);render()};
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{state.page=b.dataset.page;render()});
if("serviceWorker" in navigator) navigator.serviceWorker.register("./service-worker.js");
const initial=qs.get("cup")||localStorage.getItem("cupnavi:lastCup");
if(initial){document.querySelector("#cupKey").value=initial;loadCup(initial).catch(()=>{})}

function updateConnection(){
  const el=document.querySelector("#connection");
  const online=navigator.onLine;
  el.textContent=online?"● Online":"● Offline";
  el.classList.toggle("offline",!online);
}
window.addEventListener("online",updateConnection);
window.addEventListener("offline",updateConnection);
updateConnection();
