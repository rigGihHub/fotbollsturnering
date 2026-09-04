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
    favorite_table_position_from_snapshot,
    favorite_team_match_sections,
    favorite_team_primary_action_label,
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
    one_row: Callable[..., Mapping[str, Any] | None],
    all_rows: Callable[..., Sequence[Mapping[str, Any]]],
    create_notification_subscription: Callable[..., tuple[bool, str | None]],
) -> None:
    """Render team selection, favorite-team overview, actions and notifications."""
    st.markdown(
        """<div class='cn-public-follow-intro'>
          <div class='title'>Mitt lag</div>
          <div class='copy'>Följ mitt lag genom att välja lag. Då visas nästa match, plan och viktig laginformation först.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    with st.container():
        all_teams_value = "__all__"
        favorite_options = [all_teams_value] + [row["id"] for row in public_teams]
        favorite_index = favorite_options.index(requested_team_id) if requested_team_id in favorite_options else 0
        _favorite_select_key = f"public_favorite_team_{tournament_id}"

        # v443: selecting a team used to trigger Streamlit's normal widget rerun
        # and then an explicit fragment rerun. Route/state changes now happen in
        # the selectbox callback before the single normal rerun.
        def _sync_public_favorite_team() -> None:
            selected = st.session_state.get(_favorite_select_key, all_teams_value)
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(tournament_id)
                if selected == all_teams_value:
                    try:
                        del st.query_params["team"]
                    except KeyError:
                        pass
                else:
                    st.query_params["team"] = str(selected)
                    st.query_params["section"] = "team"

        favorite_selection = st.selectbox(
            "Välj lag",
            favorite_options,
            index=favorite_index,
            format_func=lambda team_id: tr("Alla lag") if team_id == all_teams_value else public_team_names.get(team_id, "Lag"),
            key=_favorite_select_key,
            help="Valet sparas i länken så cupen kan öppnas direkt med ditt lag.",
            on_change=_sync_public_favorite_team,
        )
        favorite_team_id = None if favorite_selection == all_teams_value else favorite_selection

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
        from cupnavi_core.arrangement_type import ARRANGEMENT_MATCHCAMP, normalize_arrangement_type
        _is_matchcamp = normalize_arrangement_type(
            row_value(tournament, "arrangement_type", "tournament")
        ) == ARRANGEMENT_MATCHCAMP
        try:
            table_position_text = (
                "–"
                if _is_matchcamp
                else favorite_table_position_from_snapshot(
                public_teams,
                published_matches,
                requested_team_id,
                tournament,
                row_value=row_value,
                )
            )
        except Exception:
            # A missing/incomplete table must not block the public team page.
            table_position_text = "–"

        possible_playoff = (
            None
            if _is_matchcamp
            else find_possible_playoff(
                published_matches,
                requested_team_id,
                source_team_id=source_team_id,
                row_value=row_value,
            )
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
                show_competition_status=not _is_matchcamp,
            ),
            unsafe_allow_html=True,
        )

        # v446: the hero already contains the next-match facts. Add one clear
        # action directly to that existing card instead of rendering a second
        # facts card. The callback only reuses the in-memory favorite snapshot
        # and deep-links to the exact match, so this adds zero DB reads.
        if favorite_next:
            _favorite_next_id = int(row_value(favorite_next, "id", 0) or 0)

            def _open_public_next_match() -> None:
                st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
                st.session_state[f"public_page_v167_{tournament_id}"] = "Matcher"
                if hasattr(st, "query_params"):
                    st.query_params["cup"] = str(tournament_id)
                    st.query_params["section"] = "matches"
                    st.query_params["team"] = str(requested_team_id)
                    if _favorite_next_id:
                        st.query_params["match"] = str(_favorite_next_id)

            _primary_match_action = favorite_team_primary_action_label(
                favorite_next,
                now=now,
                row_value=row_value,
            )
            st.button(
                _primary_match_action,
                key=f"favorite_next_match_btn_{tournament_id}_{requested_team_id}_{_favorite_next_id}",
                use_container_width=True,
                type="primary",
                help="Öppnar exakt nästa match med matchdetaljer direkt.",
                on_click=_open_public_next_match,
            )

            # v447: put navigation to the next pitch directly beside the match-day
            # action. It remains lazy: the venue lookup only happens after the
            # visitor explicitly asks for directions, so first paint stays free.
            show_directions = st.toggle(
                f"📍 Hitta till {public_pitch_label(favorite_next)}",
                value=False,
                key=f"public_team_directions_{tournament_id}_{requested_team_id}",
                help="Hämtar vägbeskrivningen först när du behöver den.",
            )
            if show_directions:
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
                else:
                    st.caption("Ingen vägbeskrivningslänk finns för nästa plan ännu.")

        _team_sections = favorite_team_match_sections(
            favorite_snapshot,
            now=now,
            row_value=row_value,
        )
        _recent = _team_sections["recent"]
        _upcoming = _team_sections["upcoming"]
        if _recent:
            _last = _recent[0]
            st.markdown("**Senaste resultat**")
            st.caption(
                f"{source_label(_last['home_source'])} "
                f"{row_value(_last, 'home_score', '–')}–{row_value(_last, 'away_score', '–')} "
                f"{source_label(_last['away_source'])}"
            )
        if _upcoming:
            st.markdown("**Min cup · kommande matcher**")
            st.caption("Ditt personliga schema – i tidsordning, med plan direkt på varje match.")
            _current_day = None
            for _index, _match in enumerate(_upcoming):
                _start_text = swedish_datetime(_match['scheduled_start'])
                _day_label = _start_text.split(" ")[0] if " " in _start_text else _start_text
                if _day_label != _current_day:
                    _current_day = _day_label
                    st.markdown(f"**{_day_label}**")
                _next_marker = "Nästa · " if _index == 0 else ""
                st.caption(
                    f"{_next_marker}{_start_text} · "
                    f"{public_pitch_label(_match)} · "
                    f"{source_label(_match['home_source'])} – {source_label(_match['away_source'])}"
                )

        def _open_public_team_matches() -> None:
            st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
            st.session_state[f"public_page_v167_{tournament_id}"] = "Matcher"
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(tournament_id)
                st.query_params["section"] = "matches"
                st.query_params["team"] = str(requested_team_id)

        def _clear_public_favorite_team() -> None:
            st.session_state[_favorite_select_key] = all_teams_value
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(tournament_id)
                st.query_params["section"] = "team"
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass

        team_action_1, team_action_2 = st.columns(2)
        team_action_1.button(
            "🗓️ Visa mitt lags matcher",
            key=f"favorite_matches_btn_{tournament_id}",
            use_container_width=True,
            type="primary",
            on_click=_open_public_team_matches,
        )
        team_action_2.button(
            tr("Visa alla lag"),
            key=f"clear_favorite_team_{tournament_id}",
            use_container_width=True,
            on_click=_clear_public_favorite_team,
        )

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

        show_notification_history = st.toggle(
            "🔔 Visa senaste lagnotiser",
            value=False,
            key=f"public_team_notifications_{tournament_id}_{requested_team_id}",
            help="Hämtar de senaste notiserna för laget först när du vill läsa dem.",
        )
        if show_notification_history:
            notification_rows = all_rows(
                """SELECT * FROM notifications WHERE tournament_id=? AND (team_id=? OR team_id IS NULL)
                   ORDER BY created_at DESC,id DESC LIMIT 5""",
                (tournament_id, requested_team_id),
            )
            if notification_rows:
                with st.expander(f"🔔 Viktigt för {team_name} ({len(notification_rows)})", expanded=True):
                    for note in notification_rows:
                        st.markdown(f"**{note['title']}**  \n{note['message']}")
                        st.caption(note["created_at"].replace("T", " "))
            else:
                st.caption("Inga lagnotiser har publicerats ännu.")
        st.caption("Bokmärk sidan – lagvalet ligger i länken och följer med nästa gång.")
