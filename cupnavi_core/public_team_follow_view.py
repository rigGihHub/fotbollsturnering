"""Streamlit view for the public ``Mitt lag`` experience.

v1.276 moves the complete public team-follow panel out of ``app.py`` while
keeping persistence, table calculation and route helpers injected from the app.
The module owns presentation and interaction only; it does not own database
connections or CupNavi domain persistence.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import streamlit as st

from cupnavi_core.public_team_follow import (
    build_favorite_team_hero_html,
    build_favorite_team_snapshot,
    favorite_table_position_label,
    favorite_team_group_id,
    find_possible_playoff,
)


def render_public_team_follow(
    *,
    tournament_id: int,
    tournament: Mapping[str, Any],
    requested_team_id: int | None,
    public_teams: Sequence[Mapping[str, Any]],
    public_team_names: Mapping[int, str],
    published_matches: Sequence[Mapping[str, Any]],
    now,
    tr: Callable[[str], str],
    source_team_id: Callable[[Any], int | None],
    source_label: Callable[[Any], str],
    row_value: Callable[[Any, str, Any], Any],
    public_pitch_label: Callable[[Mapping[str, Any]], str],
    pitch_label: Callable[[int, Any], str],
    swedish_datetime: Callable[[Any], str],
    calculate_table: Callable[[int, Mapping[str, Any]], Sequence[Any]],
    one_row: Callable[..., Mapping[str, Any] | None],
    all_rows: Callable[..., Sequence[Mapping[str, Any]]],
    create_notification_subscription: Callable[..., tuple[bool, str | None]],
) -> None:
    """Render team selection, favorite-team overview, actions and notifications."""
    st.markdown("<div class='cn-public-follow-anchor'></div>", unsafe_allow_html=True)
    with st.container():
        all_teams_value = "__all__"
        favorite_options = [all_teams_value] + [row["id"] for row in public_teams]
        favorite_index = favorite_options.index(requested_team_id) if requested_team_id in favorite_options else 0
        favorite_selection = st.selectbox(
            "⭐ Följ mitt lag",
            favorite_options,
            index=favorite_index,
            format_func=lambda team_id: tr("Alla lag") if team_id == all_teams_value else public_team_names.get(team_id, "Lag"),
            key=f"public_favorite_team_{tournament_id}",
            help="Valet sparas i länken så cupen kan öppnas direkt med ditt lag.",
        )
        favorite_team_id = None if favorite_selection == all_teams_value else favorite_selection
        if favorite_team_id is not None and favorite_team_id != requested_team_id:
            if hasattr(st, "query_params"):
                st.query_params["team"] = str(favorite_team_id)
                st.query_params["cup"] = str(tournament_id)
            st.rerun()
        if favorite_team_id is None and requested_team_id is not None:
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
                st.query_params["cup"] = str(tournament_id)
            st.rerun()

        if not requested_team_id:
            return

        favorite_snapshot = build_favorite_team_snapshot(
            published_matches,
            requested_team_id,
            now=now,
            source_team_id=source_team_id,
            row_value=row_value,
        )
        favorite_next = favorite_snapshot["next_match"]

        team_name = public_team_names.get(requested_team_id, "Lag")
        table_position_text = "–"
        favorite_group_id = favorite_team_group_id(
            public_teams,
            requested_team_id,
            row_value=row_value,
        )
        if favorite_group_id:
            try:
                favorite_table = calculate_table(favorite_group_id, tournament)
                table_position_text = favorite_table_position_label(favorite_table, requested_team_id)
            except Exception:
                # A missing/incomplete table must not block the public team page.
                pass

        possible_playoff = find_possible_playoff(
            published_matches,
            requested_team_id,
            source_team_id=source_team_id,
            row_value=row_value,
        )
        st.markdown(
            build_favorite_team_hero_html(
                team_name=team_name,
                snapshot=favorite_snapshot,
                now=now,
                table_position_text=table_position_text,
                possible_playoff=possible_playoff,
                row_value=row_value,
                source_label=source_label,
                pitch_label=public_pitch_label,
                swedish_datetime=swedish_datetime,
            ),
            unsafe_allow_html=True,
        )

        team_action_1, team_action_2 = st.columns(2)
        if favorite_next:
            favorite_pitch_no = row_value(favorite_next, "pitch_number", None)
            favorite_pitch_name = pitch_label(tournament_id, favorite_pitch_no) if favorite_pitch_no else None
            venue_direction = one_row(
                """SELECT url,label FROM venue_points
                   WHERE tournament_id=? AND kind='Plan' AND url IS NOT NULL AND TRIM(url)<>''
                     AND (LOWER(label)=LOWER(?) OR LOWER(label)=LOWER(?))
                   ORDER BY id LIMIT 1""",
                (
                    tournament_id,
                    str(favorite_pitch_name or ""),
                    f"Plan {favorite_pitch_no}" if favorite_pitch_no else "",
                ),
            )
            if venue_direction:
                st.link_button(
                    f"📍 Vägbeskrivning till {venue_direction['label']}",
                    venue_direction["url"],
                    use_container_width=True,
                )
        if team_action_1.button(
            "🗓️ Visa mitt lags matcher",
            key=f"favorite_matches_btn_{tournament_id}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
            st.session_state[f"public_page_v92_{tournament_id}"] = "Matcher"
            st.rerun()
        if team_action_2.button(
            tr("Visa alla lag"),
            key=f"clear_favorite_team_{tournament_id}",
            use_container_width=True,
        ):
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
            st.rerun()

        with st.expander("🔔 Få viktiga lagnotiser via e-post", expanded=False):
            st.caption("E-postadressen måste verifieras innan några notiser skickas.")
            with st.form(f"public_notification_subscribe_{tournament_id}_{requested_team_id}"):
                notify_email = st.text_input("E-post", key=f"notify_email_{tournament_id}_{requested_team_id}")
                nc1, nc2, nc3 = st.columns(3)
                notify_schedule = nc1.checkbox("Matchtid/plan", value=True)
                notify_results = nc2.checkbox("Resultat", value=True)
                notify_messages = nc3.checkbox("Arrangörsinfo", value=True)
                consent = st.checkbox(
                    "Jag vill få CupNavi-notiser för detta lag och kan avsluta dem via länken i varje mejl."
                )
                if st.form_submit_button("Skicka verifieringsmejl", type="primary", use_container_width=True):
                    if not consent:
                        st.error("Godkänn prenumerationen först.")
                    else:
                        try:
                            ok, error = create_notification_subscription(
                                tournament_id,
                                requested_team_id,
                                notify_email,
                                notify_schedule=notify_schedule,
                                notify_results=notify_results,
                                notify_messages=notify_messages,
                            )
                            if ok:
                                st.success(
                                    "Verifieringsmejl skickat. Öppna länken i mejlet för att aktivera notiser."
                                )
                            else:
                                st.error(
                                    "Prenumerationen sparades men verifieringsmejlet kunde inte skickas: "
                                    f"{error}"
                                )
                        except ValueError as exc:
                            st.error(str(exc))

        notification_rows = all_rows(
            """SELECT * FROM notifications WHERE tournament_id=? AND (team_id=? OR team_id IS NULL)
               ORDER BY created_at DESC,id DESC LIMIT 5""",
            (tournament_id, requested_team_id),
        )
        if notification_rows:
            with st.expander(f"🔔 Viktigt för {team_name} ({len(notification_rows)})", expanded=False):
                for note in notification_rows:
                    st.markdown(f"**{note['title']}**  \n{note['message']}")
                    st.caption(note["created_at"].replace("T", " "))
        st.caption("Bokmärk sidan – lagvalet ligger i länken och följer med nästa gång.")
