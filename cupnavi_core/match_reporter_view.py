"""Pure presentation helpers for the Match Reporter workspace.

No Streamlit/database imports. Interactive widgets and all writes stay in the
application boundary while row projection and offline-draft markup are testable.
"""
from __future__ import annotations

import html
import json
from typing import Any, Callable, Iterable


def build_event_player_rows(players: Iterable[Any], existing_by_player_id: dict[int, Any]) -> list[dict[str, Any]]:
    rows = []
    for player in players:
        player_id = int(player["id"])
        existing = existing_by_player_id.get(player_id)
        rows.append({
            "player_id": player_id,
            "Nr": player["player_number"],
            "Spelare": player["name"],
            "Mål": existing["goals"] if existing is not None else 0,
            "Assist": existing["assists"] if existing is not None else 0,
            "Varningar": existing["yellow_cards"] if existing is not None else 0,
            "Utvisningar": existing["red_cards"] if existing is not None else 0,
        })
    return rows


def build_reporter_columns(*, assist_enabled: bool, card_statistics_enabled: bool) -> list[str]:
    columns = ["Nr", "Spelare", "Mål"]
    if assist_enabled:
        columns.append("Assist")
    if card_statistics_enabled:
        columns.extend(["Varningar", "Utvisningar"])
    return columns


def build_offline_match_options(
    matches: Iterable[Any],
    *,
    swedish_datetime: Callable[[Any], str],
    source_label: Callable[[str], str],
) -> list[dict[str, Any]]:
    return [
        {
            "id": int(row["id"]),
            "label": (
                f"{swedish_datetime(row['scheduled_start'])} · Plan {row['pitch_number']} · "
                f"{source_label(row['home_source'])} – {source_label(row['away_source'])}"
            ),
        }
        for row in matches
    ]


def _script_json(value: Any) -> str:
    # Avoid a user-controlled label terminating the surrounding <script> block.
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build_offline_draft_html(options: list[dict[str, Any]], tournament_id: int) -> str:
    matches_json = _script_json(options)
    storage_key = f"cupnavi-offline-{int(tournament_id)}"
    return f"""
    <style>body{{font-family:Arial,sans-serif;color:#172033;margin:0}} .box{{border:1px solid #cbd5e1;border-radius:14px;padding:14px;background:#fff}}
    select,input,button{{font-size:16px;padding:9px;border:1px solid #cbd5e1;border-radius:9px}} .scores{{display:flex;gap:8px;margin:12px 0;align-items:center}} input{{width:70px}} button{{cursor:pointer;background:#ecfdf5}} #status{{font-size:12px;color:#475569;margin-top:8px}}</style>
    <div class='box'><b>Lokalt resultatutkast</b><br><small>Data sparas endast i den här webbläsaren.</small><br><br>
    <select id='m'></select><div class='scores'><input id='h' type='number' min='0' value='0'><b>–</b><input id='a' type='number' min='0' value='0'><button id='save'>Spara lokalt</button><button id='copy'>Kopiera</button></div><div id='status'></div></div>
    <script>
    const matches={matches_json}; const key={_script_json(storage_key)};
    const select=document.getElementById('m'); const h=document.getElementById('h'); const a=document.getElementById('a'); const status=document.getElementById('status');
    matches.forEach(x=>{{const o=document.createElement('option');o.value=x.id;o.textContent=x.label;select.appendChild(o)}});
    function load(){{const all=JSON.parse(localStorage.getItem(key)||'{{}}');const d=all[select.value];if(d){{h.value=d.h;a.value=d.a;status.textContent='Lokalt utkast hittat: '+d.saved}}else{{h.value=0;a.value=0;status.textContent='Inget lokalt utkast för vald match.'}}}}
    select.addEventListener('change',load); document.getElementById('save').onclick=()=>{{const all=JSON.parse(localStorage.getItem(key)||'{{}}');all[select.value]={{h:+h.value||0,a:+a.value||0,saved:new Date().toLocaleString()}};localStorage.setItem(key,JSON.stringify(all));status.textContent='Sparat lokalt på enheten.'}};
    document.getElementById('copy').onclick=async()=>{{const label=select.options[select.selectedIndex]?.text||'';const txt=label+' | '+h.value+'–'+a.value;try{{await navigator.clipboard.writeText(txt);status.textContent='Utkastet kopierades.'}}catch(e){{status.textContent=txt}}}}; load();
    </script>
    """


def referee_assignment_markdown(assignment: Any, *, swedish_datetime: Callable[[Any], str], source_label: Callable[[str], str]) -> str:
    return (
        f"**{html.escape(str(swedish_datetime(assignment['scheduled_start'])))} · "
        f"Plan {html.escape(str(assignment['pitch_number']))}**  \n"
        f"{html.escape(str(source_label(assignment['home_source'])))} – "
        f"{html.escape(str(source_label(assignment['away_source'])))}"
    )
