"""Public tournament shell rendering extracted from the Streamlit monolith.

The module owns presentation for the public hero and information-screen mode.
Database/domain helpers are injected by app.py so persistence and tournament
business rules stay in their existing layers.
"""
from __future__ import annotations

import html
from datetime import datetime, timedelta



SCREEN_REFRESH_MS = 30_000


def build_public_hero_html(
    tournament,
    *,
    lifecycle_status: str,
    cup_date_label,
    row_value,
    translate,
) -> str:
    """Build the public cup hero without depending on Streamlit state or the DB."""
    if lifecycle_status == "completed":
        status_html = "<span class='cn-hero-status completed'>🏆 Avslutad</span>"
    elif lifecycle_status == "live":
        status_html = "<span class='cn-hero-status live'>● Pågår</span>"
    else:
        status_html = "<span class='cn-hero-status upcoming'>Kommande</span>"

    location = html.escape(tournament["location"] or "Spelort ej angiven")
    hero_meta = f"{html.escape(str(cup_date_label(tournament)))} · {location}"
    sport = html.escape(str(row_value(tournament, "sport", "Fotboll")))
    return (
        "<section class='cup-hero cn611-public-cover'>"
        "<div class='cn611-cover-kicker'>"
        f"<span class='cn611-cover-brand'>CUPNAVI</span><span class='cn611-cover-edition'>{html.escape(translate('Turneringsöversikt'))}</span>"
        "</div>"
        "<div class='cn611-cover-main'>"
        "<div class='cn611-cover-copy'>"
        f"<div class='title'>{html.escape(tournament['name'])}</div>"
        f"<div class='meta'>{hero_meta}</div>"
        "</div>"
        f"<div class='cn611-cover-status'>{status_html}</div>"
        "</div>"
        "<div class='cn611-cover-footer'>"
        f"<span class='cn611-cover-sport'>{sport}</span>"
        "<span class='cn611-cover-slogan'>Mer cup. Mindre kaos.</span>"
        "<span class='cn611-cover-index'>MATCHDAY / 01</span>"
        "</div>"
        "</section>"
    )


def _screen_matches_html(rows, kind: str, *, pitch_label) -> str:
    if not rows:
        return "<div class='cn-screen-muted'>Inga matcher just nu.</div>"
    out = []
    for start, match, label in rows:
        if kind == "recent":
            info = f"<span class='cn-screen-score'>{int(match['home_score'])}–{int(match['away_score'])}</span>"
        else:
            info = (
                f"<span class='cn-screen-time'>{start.strftime('%H:%M')}</span> · "
                f"{html.escape(pitch_label(match))}"
            )
        out.append(
            "<div class='cn-screen-match'>"
            f"<div><b>{html.escape(label)}</b></div><div>{info}</div></div>"
        )
    return "".join(out)


def render_public_screen_mode(
    tournament_id,
    tournament,
    published_matches,
    *,
    now: datetime,
    public_cup_url,
    source_label,
    pitch_label,
    match_duration_minutes,
    calculate_all_group_tables,
    all_rows,
) -> None:
    """Render the auto-refreshing public information-screen mode."""
    import pandas as pd
    import streamlit as st
    import streamlit.components.v1 as components

    screen_exit_url = public_cup_url(tournament_id)
    st.markdown(
        """<style>
          [data-testid="stSidebar"], [data-testid="stHeader"] {display:none !important;}
          .stApp .block-container {max-width:1600px !important;padding:1.2rem 2rem 2rem !important;}
          .cn-persistent-brand,.cn-fixed-share {display:none !important;}
          .cn-screen-head{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:18px}
          .cn-screen-title{font-size:36px;font-weight:950;letter-spacing:-.04em;color:#102630}.cn-screen-meta{color:#536a72;font-size:14px;font-weight:700}
          .cn-screen-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.cn-screen-card{background:#fffdf8;border:1.5px solid #aebbb6;border-radius:16px 16px 16px 6px;padding:16px;box-shadow:0 2px 0 rgba(16,38,48,.08),0 10px 24px rgba(16,38,48,.05)}
          .cn-screen-card h3{margin:0 0 10px;padding-bottom:9px;border-bottom:4px solid #00a7b7;color:#102630;font:950 13px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.07em;text-transform:uppercase}.cn-screen-match{padding:10px 0;border-top:1px solid #e1e5e0}.cn-screen-match:first-of-type{border-top:0}.cn-screen-score{display:inline-block;background:#020708;color:#f4fff8;border-radius:5px;padding:3px 7px;font:950 24px/1 ui-monospace,SFMono-Regular,Menlo,monospace}.cn-screen-time{font:900 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:#102630}.cn-screen-muted{color:#667982}
          @media(max-width:900px){.cn-screen-grid{grid-template-columns:1fr}.cn-screen-title{font-size:27px}}
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='cn-screen-head'><div><div class='cn-screen-title'>🏆 {html.escape(tournament['name'])}</div>"
        "<div class='cn-screen-meta'>Informationsskärm · uppdateras automatiskt</div></div>"
        f"<a href='{html.escape(screen_exit_url, quote=True)}'>← Till cupsidan</a></div>",
        unsafe_allow_html=True,
    )
    components.html(
        f"<script>setTimeout(function(){{window.parent.location.reload();}},{SCREEN_REFRESH_MS});</script>",
        height=0,
    )

    live_rows = []
    upcoming_rows = []
    recent_rows = []
    duration = max(20, match_duration_minutes(tournament))
    for match in published_matches:
        start = datetime.fromisoformat(match["scheduled_start"])
        label = f"{source_label(match['home_source'])} – {source_label(match['away_source'])}"
        if match["home_score"] is not None and match["away_score"] is not None:
            recent_rows.append((start, match, label))
        elif start <= now <= start + timedelta(minutes=duration):
            live_rows.append((start, match, label))
        elif start >= now:
            upcoming_rows.append((start, match, label))

    recent_rows = sorted(recent_rows, reverse=True)[:6]
    upcoming_rows = sorted(upcoming_rows)[:8]
    live_rows = sorted(live_rows)[:8]
    st.markdown(
        "<div class='cn-screen-grid'>"
        f"<div class='cn-screen-card'><h3>🔴 Pågår / nu</h3>{_screen_matches_html(live_rows, 'live', pitch_label=pitch_label)}</div>"
        f"<div class='cn-screen-card'><h3>⏭ Kommande</h3>{_screen_matches_html(upcoming_rows, 'upcoming', pitch_label=pitch_label)}</div>"
        f"<div class='cn-screen-card'><h3>✅ Senaste resultat</h3>{_screen_matches_html(recent_rows, 'recent', pitch_label=pitch_label)}</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    table_bundle = calculate_all_group_tables(tournament_id, tournament)
    screen_groups = table_bundle["groups"][:4]
    if screen_groups:
        st.markdown("### Tabeller")
        cols = st.columns(min(2, len(screen_groups)))
        for idx, group in enumerate(screen_groups):
            table = table_bundle["tables"].get(int(group["id"]), [])
            rows = [data for _team_id, data in table]
            with cols[idx % len(cols)]:
                st.markdown(f"**{html.escape(group['name'])}**")
                if rows:
                    st.dataframe(
                        pd.DataFrame(rows)[["Lag", "S", "MS", "P"]],
                        hide_index=True,
                        use_container_width=True,
                    )

    sponsors = all_rows(
        "SELECT * FROM sponsors WHERE tournament_id=? AND active=1 ORDER BY sort_order,id LIMIT 8",
        (tournament_id,),
    )
    if sponsors:
        st.caption("Partners: " + " · ".join(sponsor["name"] for sponsor in sponsors))
