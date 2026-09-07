"""Streamlit view for the public ``Mitt lag`` experience.

v1.276 moves the complete public team-follow panel out of ``app.py`` while
keeping persistence, table calculation and route helpers injected from the app.
The module owns presentation and interaction only; it does not own database
connections or CupNavi domain persistence.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence
import html

import streamlit as st

from cupnavi_core.public_team_follow import (
    build_favorite_team_hero_html,
    build_favorite_team_snapshot,
    favorite_table_position_from_snapshot,
    favorite_team_match_sections,
    favorite_team_primary_action_label,
    find_possible_playoff,
    build_multi_favorite_timeline,
    build_family_next_step,
    build_family_travel_guidance,
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
    match_duration_minutes: Callable[..., int],
) -> None:
    """Render team selection, favorite-team overview, actions and notifications."""
    st.markdown(
        """<div class='cn-public-follow-intro'>
          <div class='title'>Mina lag</div>
          <div class='copy'>Följ ett eller flera lag – även i olika klasser. Nästa match och senaste resultat visas först.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    with st.container():
        team_ids = [int(row["id"]) for row in public_teams]
        team_by_id = {int(row["id"]): row for row in public_teams}
        _favorites_key = f"public_favorite_teams_{tournament_id}"

        def _team_choice_label(team_id: int) -> str:
            row = team_by_id.get(int(team_id), {})
            name = public_team_names.get(int(team_id), "Lag")
            age_class = str(row_value(row, "age_class", "") or "").strip()
            return f"{name} · {age_class}" if age_class else name

        # v466: multiple favourites can survive a shared/bookmarked public URL.
        _url_favorites = []
        if hasattr(st, "query_params"):
            raw_favorites = str(st.query_params.get("teams", "") or "")
            for token in raw_favorites.split(","):
                try:
                    team_id = int(token.strip())
                except (TypeError, ValueError):
                    continue
                if team_id in team_ids and team_id not in _url_favorites:
                    _url_favorites.append(team_id)
        if requested_team_id in team_ids and requested_team_id not in _url_favorites:
            _url_favorites.insert(0, int(requested_team_id))

        if _favorites_key not in st.session_state:
            st.session_state[_favorites_key] = _url_favorites

        def _sync_public_favorite_teams() -> None:
            selected = [
                int(team_id) for team_id in (st.session_state.get(_favorites_key) or [])
                if int(team_id) in team_ids
            ]
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(tournament_id)
                st.query_params["section"] = "team"
                if selected:
                    st.query_params["teams"] = ",".join(str(team_id) for team_id in selected)
                    st.query_params["team"] = str(selected[0])
                else:
                    for key in ("team", "teams"):
                        try:
                            del st.query_params[key]
                        except KeyError:
                            pass

        favorite_team_ids = st.multiselect(
            "Mina favoritlag",
            team_ids,
            default=[team_id for team_id in st.session_state.get(_favorites_key, []) if team_id in team_ids],
            format_func=_team_choice_label,
            key=_favorites_key,
            help="Du kan följa flera lag samtidigt, även lag i olika ålders- eller tävlingsklasser.",
            on_change=_sync_public_favorite_teams,
        )
        favorite_team_ids = [int(team_id) for team_id in favorite_team_ids if int(team_id) in team_ids]

        if not favorite_team_ids:
            st.info("Välj ett eller flera lag för att skapa din personliga cupöversikt.")
            return

        # The first favourite is the active detailed team; all favourites get a
        # compact overview below. Opening another favourite simply makes it first.
        active_team_id = int(requested_team_id) if requested_team_id in favorite_team_ids else int(favorite_team_ids[0])
        requested_team_id = active_team_id

        if len(favorite_team_ids) > 1:
            st.markdown("**Mina lag · överblick**")
            for _fav_id in favorite_team_ids:
                _fav_snapshot = build_favorite_team_snapshot(
                    published_matches,
                    _fav_id,
                    now=now,
                    source_team_id=source_team_id,
                    row_value=row_value,
                )
                _fav_next = _fav_snapshot.get("next_match")
                _fav_last = _fav_snapshot.get("latest_match")
                _next_text = (
                    f"{swedish_datetime(_fav_next['scheduled_start'])} · {public_pitch_label(_fav_next)}"
                    if _fav_next else "Ingen kommande match"
                )
                _last_text = (
                    f"{source_label(_fav_last['home_source'])} "
                    f"{row_value(_fav_last, 'home_score', '–')}–{row_value(_fav_last, 'away_score', '–')} "
                    f"{source_label(_fav_last['away_source'])}"
                    if _fav_last else "Inget resultat ännu"
                )
                st.markdown(
                    f"""<div class="cn-multi-favorite-card">
                      <div class="team">{html.escape(_team_choice_label(_fav_id))}</div>
                      <div class="next">Nästa: {html.escape(_next_text)}</div>
                      <div class="last">Senaste: {html.escape(_last_text)}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if int(_fav_id) != int(active_team_id):
                    def _open_favorite(team_id=int(_fav_id)) -> None:
                        ordered = [team_id] + [x for x in st.session_state.get(_favorites_key, []) if int(x) != team_id]
                        st.session_state[_favorites_key] = ordered
                        if hasattr(st, "query_params"):
                            st.query_params["team"] = str(team_id)
                            st.query_params["teams"] = ",".join(str(x) for x in ordered)
                            st.query_params["section"] = "team"
                    st.button(
                        f"Öppna {_team_choice_label(_fav_id)}",
                        key=f"open_favorite_{tournament_id}_{_fav_id}",
                        use_container_width=True,
                        on_click=_open_favorite,
                    )

            _timeline = build_multi_favorite_timeline(
                published_matches,
                favorite_team_ids,
                now=now,
                source_team_id=source_team_id,
                row_value=row_value,
                proximity_minutes=60,
                limit=8,
            )
            if _timeline["matches"]:
                _family_step = build_family_next_step(
                    _timeline,
                    now=now,
                    row_value=row_value,
                )
                _next_item = _family_step["next_item"]
                if _next_item is not None:
                    _next_match = _next_item["match"]
                    _next_favorites = " + ".join(
                        _team_choice_label(team_id)
                        for team_id in _next_item["favorite_team_ids"]
                    )
                    _next_in = _family_step["minutes_until_next"]
                    _when_text = "Nu" if _next_in <= 0 else f"Om {_next_in} min"
                    _move_text = ""
                    _travel_text = ""
                    _travel_status = "unknown"
                    if _family_step["following_item"] is not None:
                        _gap = _family_step["gap_minutes"]
                        if _family_step["pitch_change"]:
                            _move_text = (
                                f"Nästa favoritmatch startar {_gap} min senare · "
                                f"byt plan {_family_step['from_pitch']} → {_family_step['to_pitch']}."
                            )
                        else:
                            _move_text = f"Nästa favoritmatch startar {_gap} min senare · samma plan."

                        # v469: only load travel/rule data when a second favourite
                        # match actually exists. The ordinary public first paint
                        # and single-favourite path stay untouched.
                        _family_rules_row = one_row(
                            "SELECT * FROM schedule_rules WHERE tournament_id=?",
                            (tournament_id,),
                        )
                        _family_match_minutes = match_duration_minutes(
                            dict(_family_rules_row) if _family_rules_row is not None else {}
                        )
                        _family_travel_matrix = {}
                        if _family_step["pitch_change"]:
                            _family_travel_rows = all_rows(
                                """SELECT from_pitch_number,to_pitch_number,minutes
                                   FROM pitch_travel_times WHERE tournament_id=?""",
                                (tournament_id,),
                            )
                            _family_travel_matrix = {
                                (int(row["from_pitch_number"]), int(row["to_pitch_number"])): max(0, int(row["minutes"] or 0))
                                for row in _family_travel_rows
                            }
                        _travel = build_family_travel_guidance(
                            _family_step,
                            _family_travel_matrix,
                            match_duration_minutes=_family_match_minutes,
                        )
                        _travel_status = _travel["status"]
                        if _travel["status"] == "same_pitch":
                            _travel_text = (
                                f"Efter beräknad matchslut: {_travel['margin_minutes']} min till nästa avspark · ingen planförflyttning."
                            )
                        elif _travel["available"]:
                            _travel_text = (
                                f"Planerad förflyttning: {_travel['planned_transfer_minutes']} min · "
                                f"marginal efter beräknad matchslut: {_travel['margin_minutes']} min."
                            )
                        elif _family_step["pitch_change"]:
                            _travel_text = "Förflyttningstid mellan planerna saknas."

                    st.markdown(
                        f"""<div class="cn-family-next-card">
                          <div class="eyebrow">Nästa för familjen</div>
                          <div class="title">{html.escape(_when_text)} · {html.escape(_next_favorites)}</div>
                          <div class="match">{html.escape(source_label(_next_match['home_source']))} – {html.escape(source_label(_next_match['away_source']))}</div>
                          <div class="meta">{html.escape(swedish_datetime(_next_match['scheduled_start']))} · {html.escape(public_pitch_label(_next_match))}</div>
                          {f'<div class="move">⚠ {html.escape(_move_text)}</div>' if _family_step["tight_turnaround"] and _move_text else (f'<div class="move">{html.escape(_move_text)}</div>' if _move_text else '')}
                          {f'<div class="travel {"warn" if _travel_status in ("insufficient", "tight", "missing_travel_time") else ""}">{html.escape(_travel_text)}</div>' if _travel_text else ''}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    _family_pitch_no = row_value(_next_match, "pitch_number", None)
                    _show_family_directions = st.toggle(
                        f"📍 Vägbeskrivning till {public_pitch_label(_next_match)}",
                        value=False,
                        key=f"family_next_directions_{tournament_id}_{_family_pitch_no}",
                        help="Hämtar vägbeskrivningen först när du behöver den.",
                    )
                    if _show_family_directions:
                        _family_pitch_name = (
                            pitch_label(tournament_id, _family_pitch_no)
                            if _family_pitch_no else None
                        )
                        _family_direction = one_row(
                            """SELECT label,url FROM venue_points
                               WHERE tournament_id=? AND kind='Plan' AND url IS NOT NULL AND TRIM(url)<>''
                                 AND (LOWER(label)=LOWER(?) OR LOWER(label)=LOWER(?))
                               ORDER BY id LIMIT 1""",
                            (
                                tournament_id,
                                str(_family_pitch_name or ""),
                                f"Plan {_family_pitch_no}" if _family_pitch_no else "",
                            ),
                        )
                        if _family_direction:
                            st.link_button(
                                f"📍 Öppna vägbeskrivning · {_family_direction['label']}",
                                _family_direction["url"],
                                use_container_width=True,
                            )
                        else:
                            st.caption("Ingen vägbeskrivningslänk finns för nästa familjematch ännu.")

                st.markdown("**Mina lag · kommande**")
                st.caption("Alla favoritlag i samma tidsordning. ⚠ betyder att två favoritmatcher ligger inom 60 minuter.")
                for _item in _timeline["matches"]:
                    _match = _item["match"]
                    _match_id = int(row_value(_match, "id", 0) or 0)
                    _fav_names = " + ".join(
                        _team_choice_label(team_id)
                        for team_id in _item["favorite_team_ids"]
                    )
                    _warning = "⚠ " if _match_id in _timeline["conflict_match_ids"] else ""
                    st.markdown(
                        f"""<div class="cn-favorite-timeline-row">
                          <div class="time">{html.escape(swedish_datetime(_match['scheduled_start']))}</div>
                          <div class="teams">{html.escape(source_label(_match['home_source']))} – {html.escape(source_label(_match['away_source']))}</div>
                          <div class="meta">{_warning}{html.escape(_fav_names)} · {html.escape(public_pitch_label(_match))}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

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

        # v462: latest_match already exists in the in-memory favorite snapshot.
        # Reuse it directly so the first-screen improvement adds no extra work.
        _last = favorite_snapshot.get("latest_match")
        if _last:
            st.markdown(
                f"""<div class="cn-follow-latest-result">
                  <span class="label">Senaste</span>
                  <span class="teams">{source_label(_last['home_source'])} "
                f"{row_value(_last, 'home_score', '–')}–{row_value(_last, 'away_score', '–')} "
                f"{source_label(_last['away_source'])}</span></div>""",
                unsafe_allow_html=True,
            )
            _last_match_id = int(row_value(_last, "id", 0) or 0)

            def _open_latest_scorers() -> None:
                st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
                st.session_state[f"public_page_v167_{tournament_id}"] = "Matcher"
                if hasattr(st, "query_params"):
                    st.query_params["cup"] = str(tournament_id)
                    st.query_params["section"] = "matches"
                    st.query_params["team"] = str(requested_team_id)
                    if _last_match_id:
                        st.query_params["match"] = str(_last_match_id)

            with st.expander("Mer om senaste resultatet", expanded=False):
                st.button(
                    "⚽ Visa målskyttar och kort",
                    key=f"favorite_latest_scorers_{tournament_id}_{requested_team_id}_{_last_match_id}",
                    use_container_width=True,
                    help="Öppnar senaste matchen med registrerade målskyttar och kort.",
                    on_click=_open_latest_scorers,
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

            def _open_next_match_weather() -> None:
                st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
                st.session_state[f"public_page_v167_{tournament_id}"] = "Matcher"
                # Reuse the existing opt-in weather control. Forecast/network
                # work still starts only after the visitor explicitly taps here.
                st.session_state[f"public_matches_weather_{tournament_id}"] = True
                if hasattr(st, "query_params"):
                    st.query_params["cup"] = str(tournament_id)
                    st.query_params["section"] = "matches"
                    st.query_params["team"] = str(requested_team_id)
                    if _favorite_next_id:
                        st.query_params["match"] = str(_favorite_next_id)

            with st.expander("Väder & vägbeskrivning", expanded=False):
                st.button(
                    "🌦️ Väder för nästa match",
                    key=f"favorite_next_weather_{tournament_id}_{requested_team_id}_{_favorite_next_id}",
                    use_container_width=True,
                    help="Öppnar nästa match och aktiverar väderprognosen först när du ber om den.",
                    on_click=_open_next_match_weather,
                )

                # Navigation remains truly lazy: the venue lookup only happens
                # after the visitor explicitly asks for directions.
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
                            f"📍 Öppna vägbeskrivning · {venue_direction['label']}",
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
        _upcoming = _team_sections["upcoming"]
        if _upcoming:
            st.markdown("**Kommande matcher**")
            _visible_upcoming = _upcoming[:3]
            for _index, _match in enumerate(_visible_upcoming):
                _start_text = swedish_datetime(_match['scheduled_start'])
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
            st.session_state[_favorites_key] = []
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(tournament_id)
                st.query_params["section"] = "team"
                for key in ("team", "teams"):
                    try:
                        del st.query_params[key]
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
            "Rensa favoriter",
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
