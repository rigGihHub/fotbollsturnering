"""Public match-card presentation extracted from the Streamlit monolith.

The module owns card rendering and weather display only. Match filtering,
query parameters, event loading and tournament state remain in app.py.
"""
import html
from datetime import datetime, timedelta

import streamlit as st

from cupnavi_core.match_status import MATCH_FINISHED, MATCH_HALFTIME, MATCH_LIVE, normalize_match_status


def render_public_match_cards(
    matches,
    *,
    tournament,
    show_results=None,
    show_weather=False,
    events_by_match=None,
    row_value,
    fetch_weather_forecast,
    public_team_by_id,
    public_team_names,
    public_source_team_id,
    public_source_label,
    swedish_datetime,
    weather_for_match,
    weather_label,
    match_kit_colors,
    kit_background_for_team,
    public_match_events_html,
    public_pitch_label,
    public_referee_label,
    render_empty_state,
    now,
):
    """Ett gemensamt matchkort: spelade matcher visar resultat, kommande visar VS."""
    events_by_match = events_by_match or {}
    weather_forecast, weather_status = ({}, "")
    if show_weather:
        weather_now = datetime.now()
        weather_horizon = weather_now + timedelta(days=16)
        forecastable = False
        for _weather_match in matches:
            try:
                _weather_start = datetime.fromisoformat(str(row_value(_weather_match, "scheduled_start", "")))
                if weather_now - timedelta(hours=3) <= _weather_start <= weather_horizon:
                    forecastable = True
                    break
            except (TypeError, ValueError):
                continue
        if forecastable:
            weather_forecast, weather_status = fetch_weather_forecast(tournament["location"] or "")
        else:
            weather_status = ""

    st.markdown(
        """
        <style>
          .public-match-card,
          .public-match-card div,
          .public-match-card span,
          .public-match-card b { color:#172033 !important; }
          .public-match-card .match-stage { color:#334155 !important; }
          .public-match-card .match-meta { color:#475569 !important; }
          .public-match-card .kit-label,
          .public-match-card .match-referee,
          .public-match-card .match-weather { color:#64748b !important; }
          .public-match-card .match-score { color:#0f172a !important;font-weight:900 !important; }
          .public-match-card .public-team-name { font-size:18px !important;line-height:1.18;font-weight:850; }
          .public-match-secondary{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#64748b!important}
          .cn-match-card-top{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px}
          .cn-match-time{font-size:20px;font-weight:900;letter-spacing:-.03em;line-height:1;color:#0f172a!important}
          .cn-match-place{font-size:12px;font-weight:760;color:#475569!important}
          .cn-match-context{text-align:center;min-width:0}
          .cn-match-context .match-stage{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.045em}
          .cn-match-context .match-number{font-size:10px;color:#94a3b8!important;margin-top:1px}
          .cn-match-status{text-align:right}
          .cn-match-relative{display:block;font-size:10px;font-weight:760;color:#166534!important;margin-top:3px}
          .cn-match-teams{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:10px;align-items:center;margin-top:10px}
          .cn-match-team{min-width:0}
          .cn-match-team.away{text-align:right}
          .cn-match-teamline{display:flex;align-items:center;gap:6px;min-width:0}
          .cn-match-team.away .cn-match-teamline{justify-content:flex-end}
          .cn-match-kit{display:inline-block;width:16px;height:12px;border:1px solid #64748b;border-radius:3px;flex:0 0 16px}
          @media(max-width:760px){
            .public-match-card .public-team-name{font-size:16px!important}
            .public-match-secondary{display:block;text-align:center}
            .cn-match-card-top{grid-template-columns:auto 1fr auto;gap:7px}
            .cn-match-time{font-size:18px}
            .cn-match-place{font-size:11px}
            .cn-match-teams{gap:7px}
            .cn-match-context .match-stage{font-size:10px}
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not matches:
        render_empty_state(
            "Inga matcher i det här urvalet",
            "Ändra filtret eller välj Alla matcher för att se hela spelschemat.",
            symbol="—",
        )
        return

    for number, match_row in enumerate(matches, 1):
        home = public_team_by_id.get(public_source_team_id(match_row["home_source"]))
        away = public_team_by_id.get(public_source_team_id(match_row["away_source"]))
        home_name = home["name"] if home else public_source_label(match_row["home_source"])
        away_name = away["name"] if away else public_source_label(match_row["away_source"])
        start = swedish_datetime(match_row["scheduled_start"])
        weather_text = ""
        if show_weather:
            try:
                match_weather = weather_for_match(weather_forecast, row_value(match_row, "scheduled_start"))
                weather_text = weather_label(match_weather) if weather_forecast else weather_status
            except Exception:
                weather_text = "Väderprognosen kan inte visas för den här matchen."

        _, _, away_kit_used = match_kit_colors(home, away)
        home_kit_bg = kit_background_for_team(home, "home") if home else "#94a3b8"
        away_selected_kit = "away" if away_kit_used else "home"
        away_kit_bg = kit_background_for_team(away, away_selected_kit) if away else "#94a3b8"

        match_is_played = match_row["home_score"] is not None and match_row["away_score"] is not None
        explicit_status = normalize_match_status(
            row_value(match_row, "match_status", None),
            has_result=match_is_played,
        )
        row_show_results = match_is_played if show_results is None else bool(show_results)
        match_start_dt = None
        try:
            match_start_dt = datetime.fromisoformat(str(row_value(match_row, "scheduled_start", "")))
        except (TypeError, ValueError):
            pass
        time_label = match_start_dt.strftime("%H:%M") if match_start_dt else start
        pitch_text = public_pitch_label(match_row)
        relative_text = ""
        if match_start_dt and explicit_status not in {MATCH_FINISHED, MATCH_LIVE, MATCH_HALFTIME} and not match_is_played:
            minutes_until = int((match_start_dt - now).total_seconds() // 60)
            if 0 <= minutes_until < 60:
                relative_text = f"om {minutes_until} min"
            elif 60 <= minutes_until < 180:
                relative_text = f"om {minutes_until // 60} h {minutes_until % 60:02d} min"

        if row_show_results:
            center_text = f"{match_row['home_score']}–{match_row['away_score']}"
            if match_row["home_penalties"] is not None:
                center_text += f" ({match_row['home_penalties']}–{match_row['away_penalties']} str.)"
            status_text, status_class = "SLUT", "status-finished"
            match_events_html = public_match_events_html(
                match_row["id"],
                match_row=match_row,
                rows=events_by_match.get(match_row["id"], []),
                team_names=public_team_names,
            )
        else:
            center_text = "VS"
            match_events_html = ""
            if explicit_status == MATCH_FINISHED:
                status_text, status_class = "SLUT", "status-finished"
            elif explicit_status == MATCH_HALFTIME:
                status_text, status_class = "PAUS", "status-live"
            elif explicit_status == MATCH_LIVE:
                status_text, status_class = "PÅGÅR", "status-live"
            else:
                status_text, status_class = "KOMMANDE", "status-upcoming"

        # Keep the whole card as one compact HTML block. Markdown can interpret
        # indented HTML after an injected block as a code block, which previously
        # exposed the referee <span> as literal text in the public card.
        weather_html = (
            f'<span class="match-weather">{html.escape(weather_text)}</span>'
            if show_weather and weather_text else ""
        )
        referee_html = (
            f'<span class="match-referee">Domare: '
            f'{html.escape(public_referee_label(match_row) or "Ej tillsatt")}</span>'
        )
        match_number = row_value(match_row, "match_no", number) or number
        relative_html = (
            f'<span class="cn-match-relative">{html.escape(relative_text)}</span>'
            if relative_text else ""
        )
        card_state_class = (
            "is-live" if explicit_status in {MATCH_LIVE, MATCH_HALFTIME}
            else ("is-finished" if row_show_results or explicit_status == MATCH_FINISHED else "is-upcoming")
        )
        card_html = (
            f'<div class="public-match-card {card_state_class}" style="border:1px solid #d1d5db;border-radius:14px;'
            'padding:14px;margin:10px 0;background:#ffffff;color:#172033">'
            '<div class="cn-match-card-top">'
            f'<div><div class="cn-match-time">{html.escape(time_label)}</div>'
            f'<div class="cn-match-place">{html.escape(pitch_text)}</div></div>'
            f'<div class="cn-match-context"><div class="match-stage">{html.escape(str(match_row["stage"]))}</div>'
            f'<div class="match-number">Match {html.escape(str(match_number))}</div></div>'
            f'<div class="cn-match-status"><span class="status-pill {status_class}">{html.escape(status_text)}</span>{relative_html}</div>'
            '</div>'
            '<div class="cn-match-teams">'
            f'<div class="cn-match-team"><div class="cn-match-teamline"><span class="cn-match-kit" style="background:{home_kit_bg}"></span>'
            f'<b class="public-team-name">{html.escape(home_name)}</b></div>'
            '<small class="kit-label">Hemmalag</small></div>'
            f'<div class="match-score" style="font-size:21px">{html.escape(center_text)}</div>'
            f'<div class="cn-match-team away"><div class="cn-match-teamline"><b class="public-team-name">{html.escape(away_name)}</b>'
            f'<span class="cn-match-kit" style="background:{away_kit_bg}"></span></div>'
            f'<small class="kit-label">{"Bortaställ" if away_kit_used else "Hemmaställ"}</small></div>'
            '</div>'
            f'{match_events_html}'
            f'<div class="public-match-secondary">{weather_html}{referee_html}</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    if show_weather:
        st.caption("Väderprognos från Open-Meteo. Prognosen uppdateras automatiskt och kan förändras.")
