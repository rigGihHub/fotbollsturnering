"""Public match-card presentation extracted from the Streamlit monolith.

The module owns card rendering and weather display only. Match filtering,
query parameters, event loading and tournament state remain in app.py.
"""
import html
from datetime import datetime, timedelta

import streamlit as st


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
          .public-match-card .match-stage { color:#ffffff !important; }
          .public-match-card .match-meta { color:#475569 !important; }
          .public-match-card .kit-label,
          .public-match-card .match-referee,
          .public-match-card .match-weather { color:#64748b !important; }
          .public-match-card .match-score { color:#0f172a !important;font-weight:900 !important; }
          .public-match-card .public-team-name { font-size:18px !important;line-height:1.2;font-weight:850; }
          .public-match-secondary{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#64748b!important}
          @media(max-width:760px){
            .public-match-card .public-team-name{font-size:16px!important}
            .public-match-secondary{display:block;text-align:center}
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
        row_show_results = match_is_played if show_results is None else bool(show_results)

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
            match_start_dt = datetime.fromisoformat(match_row["scheduled_start"])
            if match_row["home_score"] is not None and match_row["away_score"] is not None:
                status_text, status_class = "SPELAD", "status-finished"
            elif match_start_dt <= now <= match_start_dt + timedelta(hours=2):
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
        card_html = (
            '<div class="public-match-card" style="border:1px solid #d1d5db;border-radius:14px;'
            'padding:16px;margin:12px 0;background:#ffffff;color:#172033;'
            'box-shadow:0 3px 10px rgba(15,23,42,.06)">'
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'border-bottom:1px solid #edf2f7;padding-bottom:7px;gap:12px">'
            f'<div style="display:flex;gap:6px;align-items:center"><span class="match-stage" '
            f'style="font-size:11px;font-weight:800;color:#fff;background:#166534;padding:4px 8px;'
            f'border-radius:999px">{html.escape(str(match_row["stage"]))}</span>'
            f'<span class="status-pill {status_class}">{html.escape(status_text)}</span></div>'
            f'<span class="match-meta">Match {number} · <b>{html.escape(start)}</b> · '
            f'{html.escape(public_pitch_label(match_row))}</span></div>'
            '<div style="display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);'
            'gap:12px;align-items:center;margin-top:7px;color:#0f172a">'
            f'<div><span style="display:inline-block;width:18px;height:13px;background:{home_kit_bg};'
            f'border:1px solid #64748b;border-radius:3px"></span>'
            f'<b class="public-team-name">{html.escape(home_name)}</b><br>'
            '<small class="kit-label">Hemmalag</small></div>'
            f'<div class="match-score" style="font-size:20px">{html.escape(center_text)}</div>'
            f'<div style="text-align:right"><b class="public-team-name">{html.escape(away_name)}</b> '
            f'<span style="display:inline-block;width:18px;height:13px;background:{away_kit_bg};'
            'border:1px solid #64748b;border-radius:3px"></span><br>'
            f'<small class="kit-label">{"Bortaställ" if away_kit_used else "Hemmaställ"}</small></div>'
            '</div>'
            f'{match_events_html}'
            f'<div class="public-match-secondary">{weather_html}{referee_html}</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    if show_weather:
        st.caption("Väderprognos från Open-Meteo. Prognosen uppdateras automatiskt och kan förändras.")
