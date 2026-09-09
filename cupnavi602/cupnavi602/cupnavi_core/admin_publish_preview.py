"""Compact pre-publication preview for CupNavi admin."""
from __future__ import annotations

from typing import Any, Callable


def render_publish_preview(
    *,
    st: Any,
    tournament_id: int,
    tournament: Any,
    all_rows: Callable[..., Any],
    row_value: Callable[..., Any],
    cup_date_label: Callable[..., str],
    show_heading: bool = True,
) -> None:
    """Show the essentials an organiser should verify before publishing.

    v570: the same visitor-facing preview is reused by both Kontroll and
    Publicera. ``show_heading`` lets the caller own the surrounding hierarchy.
    """
    teams = all_rows(
        """SELECT t.name AS team_name, COALESCE(g.name,'Ej gruppindelad') AS group_name
           FROM teams t LEFT JOIN groups g ON g.id=t.group_id
           WHERE t.tournament_id=? ORDER BY group_name,t.name""",
        (tournament_id,),
    )
    matches = all_rows(
        """SELECT m.match_no,m.stage,m.scheduled_start,m.pitch_number,m.home_source,m.away_source,
                  COALESCE(g.name,'') AS group_name
           FROM matches m LEFT JOIN groups g ON g.id=m.group_id
           WHERE m.tournament_id=?
           ORDER BY CASE WHEN m.scheduled_start IS NULL THEN 1 ELSE 0 END,m.scheduled_start,m.match_no,m.id""",
        (tournament_id,),
    )
    pitches = all_rows(
        "SELECT pitch_number,name,address FROM pitches WHERE tournament_id=? ORDER BY pitch_number",
        (tournament_id,),
    )

    if show_heading:
        st.markdown("### Förhandsgranska före publicering")
        st.caption("Kontrollera det publiken och lagen kommer att möta. Förhandsgranskningen ändrar ingenting.")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cup", str(row_value(tournament, "name", "–") or "–"))
        c2.metric("Datum", cup_date_label(tournament))
        c3.metric("Lag", len(teams))
        c4.metric("Matcher", len(matches))
        place = str(row_value(tournament, "location", "") or row_value(tournament, "place", "") or "Ej angiven")
        st.caption(f"{row_value(tournament, 'sport', 'Sport ej angiven')} · {place}")

    # v570: show the public information architecture before the organiser dives
    # into detailed rows. This mirrors the visitor's mental model and makes
    # optional statistics explicit instead of hiding them in setup.
    enabled_features = ["Cupinfo", "Matcher & schema", "Grupper & tabeller"]
    if bool(row_value(tournament, "enable_scorer_leaderboard", 1)):
        enabled_features.append("Skytteliga")
    if bool(row_value(tournament, "enable_assist_leaderboard", 1)):
        enabled_features.append("Assistliga")
    if bool(row_value(tournament, "enable_card_statistics", 1)):
        enabled_features.append("Kortstatistik")
    with st.container(border=True):
        st.markdown("**Publikt innehåll**")
        st.write(" · ".join(f"✓ {label}" for label in enabled_features))
        hidden = []
        if not bool(row_value(tournament, "enable_scorer_leaderboard", 1)):
            hidden.append("Skytteliga")
        if not bool(row_value(tournament, "enable_assist_leaderboard", 1)):
            hidden.append("Assistliga")
        if not bool(row_value(tournament, "enable_card_statistics", 1)):
            hidden.append("Kortstatistik")
        if hidden:
            st.caption("Dolt enligt cupens inställningar: " + ", ".join(hidden) + ".")

    with st.expander("Lag och grupper", expanded=True):
        if not teams:
            st.warning("Inga lag finns ännu.")
        else:
            groups: dict[str, list[str]] = {}
            for row in teams:
                groups.setdefault(str(row_value(row, "group_name", "Ej gruppindelad")), []).append(str(row_value(row, "team_name", "")))
            for group_name, names in groups.items():
                st.markdown(f"**{group_name}** · {len(names)} lag")
                st.write(" · ".join(names))

    with st.expander("Schema", expanded=True):
        if not matches:
            st.warning("Inget schema finns att publicera ännu.")
        else:
            preview_rows = []
            for row in matches:
                start = str(row_value(row, "scheduled_start", "") or "")
                if "T" in start:
                    date_part, time_part = start.split("T", 1)
                    start = f"{date_part} {time_part[:5]}"
                preview_rows.append({
                    "#": row_value(row, "match_no", ""),
                    "Tid": start or "Ej schemalagd",
                    "Plan": row_value(row, "pitch_number", "–") or "–",
                    "Match": f"{row_value(row, 'home_source', '–')} – {row_value(row, 'away_source', '–')}",
                    "Del": row_value(row, "group_name", "") or row_value(row, "stage", ""),
                })
            st.dataframe(preview_rows, hide_index=True, use_container_width=True)

    with st.expander("Planer och platser", expanded=False):
        if not pitches:
            st.caption("Inga separata planuppgifter registrerade.")
        else:
            pitch_rows = [
                {
                    "Plan": row_value(row, "pitch_number", ""),
                    "Namn": row_value(row, "name", ""),
                    "Adress": row_value(row, "address", "") or "–",
                }
                for row in pitches
            ]
            st.dataframe(pitch_rows, hide_index=True, use_container_width=True)

    playoff_matches = [row for row in matches if str(row_value(row, "stage", "")).lower() != "gruppspel"]
    if playoff_matches:
        with st.expander("Slutspel", expanded=False):
            for row in playoff_matches:
                st.write(
                    f"Match {row_value(row, 'match_no', '')}: "
                    f"{row_value(row, 'home_source', '–')} – {row_value(row, 'away_source', '–')}"
                )
