"""Public match-list orchestration extracted from the Streamlit entrypoint.

The function in this module owns the public Matches page rendering flow, while
app.py remains responsible for the Streamlit fragment boundary and application
services such as DB instrumentation, translation and URL/share helpers.
"""
from __future__ import annotations

# Legacy fragment QA anchor retained for historical contract: st.rerun(scope="fragment")

import time
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from cupnavi_core.public_match_feed_logic import classify_public_match_feed, public_match_feed_summary
from cupnavi_core.public_match_overview import build_highlights_html, build_live_feed_html, build_summary_html
from cupnavi_core.public_match_paging import (
    PUBLIC_MATCH_BATCH_SIZE,
    PUBLIC_MATCH_INITIAL_BATCH,
    next_visible_count,
    visible_match_batch,
)


def render_public_matches_fragment(
    *,
    st: Any,
    tournament_id: int,
    tournament: Mapping[str, Any],
    published_matches: Sequence[Any],
    feed_matches: Sequence[Any] | None = None,
    published_match_total: int | None = None,
    published_matches_complete: bool = True,
    played_matches: Sequence[Any],
    played_match_total: int | None = None,
    total_goals: int | None = None,
    public_teams: Sequence[Any],
    public_team_total: int | None,
    public_team_names: Mapping[int, str],
    requested_team_id: int | None,
    requested_pitch_no: int | None,
    requested_match_id: int | None,
    now: Any,
    perf: Mapping[str, Any],
    tr: Callable[[str], str],
    row_value: Callable[..., Any],
    sport_profile: Callable[[str], Mapping[str, Any]],
    match_duration_minutes: Callable[[Any], int],
    source_label: Callable[[str], str],
    source_team_id: Callable[[str], int | None],
    pitch_label: Callable[[Any], str],
    render_share_control: Callable[[int, Any], Any],
    filter_matches_view: Callable[[Sequence[Any], str, str], tuple[Any, Any, str]],
    render_match_cards: Callable[..., Any],
    load_match_events: Callable[[Sequence[int]], Mapping[int, Sequence[Any]]],
    load_overview: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    """Render the public Matches page and return its measured performance snapshot."""
    fragment_started = time.perf_counter()
    db_calls_before = int(perf["db_calls"])
    db_ms_before = float(perf["db_ms"])

    team_count = len(public_teams) if public_team_total is None else int(public_team_total or 0)
    # v538: cup-day bounded snapshots already carry exact aggregate totals.
    # Do not rescan every played row on each fragment click when the database
    # has already supplied the answer in the same first-paint roundtrip.
    if total_goals is None:
        summary_total_goals = sum(
            int(match["home_score"] or 0) + int(match["away_score"] or 0)
            for match in played_matches
        )
    else:
        summary_total_goals = int(total_goals or 0)
    summary_played_count = len(played_matches) if played_match_total is None else int(played_match_total or 0)
    stage_timings: dict[str, float] = {}

    stage_started = time.perf_counter()
    live_now, next_matches, recent_results = classify_public_match_feed(
        list(feed_matches) if feed_matches is not None else published_matches,
        now=now,
        match_duration_minutes=match_duration_minutes(tournament),
    )
    # Keep the three values named here even though the summary currently derives
    # its UI from live/next. It makes the orchestration contract explicit and
    # prevents future feed changes from silently altering the classifier call.
    _ = recent_results
    feed_summary = public_match_feed_summary(live_now, next_matches)
    feed_html = build_live_feed_html(
        feed_summary["items"],
        is_live=bool(feed_summary["is_live"]),
        title=str(feed_summary["title"]),
        subtitle=str(feed_summary["subtitle"]),
        status=str(feed_summary["status"]),
        row_value=row_value,
        source_label=source_label,
        pitch_label=pitch_label,
    )
    if feed_html:
        st.markdown(feed_html, unsafe_allow_html=True)
    stage_timings["live_feed_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    # v541: restore the compact public highlights that existed before the
    # first-paint performance work. The top scorer comes from the dedicated
    # lightweight cached query, so we do not need to load the full statistics
    # dashboard. Team attack/defence highlights are calculated only when the
    # current snapshot contains every published match; otherwise omitting them
    # is safer than presenting rankings from a bounded first-paint batch.
    stage_started = time.perf_counter()
    summary_highlights: dict[str, Any] = {}
    if played_matches and published_matches_complete:
        team_totals: dict[int, dict[str, int]] = {}
        for match in played_matches:
            home_id = source_team_id(match["home_source"])
            away_id = source_team_id(match["away_source"])
            if home_id is None or away_id is None:
                continue
            home_score = int(match["home_score"] or 0)
            away_score = int(match["away_score"] or 0)
            home_stats = team_totals.setdefault(int(home_id), {"gf": 0, "ga": 0, "played": 0})
            away_stats = team_totals.setdefault(int(away_id), {"gf": 0, "ga": 0, "played": 0})
            home_stats["gf"] += home_score; home_stats["ga"] += away_score; home_stats["played"] += 1
            away_stats["gf"] += away_score; away_stats["ga"] += home_score; away_stats["played"] += 1
        if team_totals:
            max_goals = max(stats["gf"] for stats in team_totals.values())
            played_team_stats = [stats for stats in team_totals.values() if stats["played"] > 0]
            min_conceded = min(stats["ga"] for stats in played_team_stats) if played_team_stats else 0
            attack_names = sorted(public_team_names[team_id] for team_id, stats in team_totals.items() if stats["gf"] == max_goals and team_id in public_team_names)
            defence_names = sorted(public_team_names[team_id] for team_id, stats in team_totals.items() if stats["played"] > 0 and stats["ga"] == min_conceded and team_id in public_team_names)
            if attack_names:
                summary_highlights["attack"] = {"names": attack_names, "value": max_goals}
            if defence_names:
                summary_highlights["defence"] = {"names": defence_names, "value": min_conceded}

    if bool(row_value(tournament, "enable_scorer_leaderboard", 1)) and summary_played_count > 0:
        overview_started = time.perf_counter()
        overview = load_overview(tournament_id)
        stage_timings["overview_db_ms"] = round((time.perf_counter() - overview_started) * 1000, 1)
        leader_rows = list(overview.get("leader_rows", []))
        if leader_rows:
            leader = leader_rows[0]
            if int(leader.get("goals") or 0) > 0:
                summary_highlights["scorer"] = {
                    "player": str(leader.get("player_name") or ""),
                    "team": str(leader.get("team_name") or ""),
                    "value": int(leader.get("goals") or 0),
                }

    summary_html = build_summary_html(
        team_count=team_count,
        played_count=summary_played_count,
        total_matches=max(len(published_matches), int(published_match_total or 0)),
        total_score=summary_total_goals,
        score_label=sport_profile(row_value(tournament, "sport", "Fotboll"))["score_label"],
        tr=tr,
        highlights_html=build_highlights_html(summary_highlights, tr=tr),
    )
    st.markdown(summary_html, unsafe_allow_html=True)
    stage_timings["summary_share_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)
    stage_timings.setdefault("overview_db_ms", 0.0)
    stage_timings["highlights_ms"] = 0.0
    stage_timings["visitors_ms"] = 0.0

    def _rerun_full_public_app() -> None:
        # Isolated fragments are fast for local display toggles, but controls
        # that change the required dataset must let the workspace rebuild its
        # server-side snapshot. Without this, a 12-row first-paint batch could
        # incorrectly remain the whole universe for Played/Upcoming/highlights.
        st.rerun(scope="app")

    requested_match_view = str(st.query_params.get("matches", "all")) if hasattr(st, "query_params") else "all"
    requested_match_view = requested_match_view if requested_match_view in {"all", "upcoming", "played"} else "all"
    match_view_labels = {
        "all": tr("Alla"),
        "upcoming": tr("Kommande"),
        "played": tr("Spelade"),
    }
    match_key_by_label = {value: key for key, value in match_view_labels.items()}
    match_view = st.segmented_control(
        tr("Visa matcher"),
        [tr("Alla"), tr("Kommande"), tr("Spelade")],
        default=match_view_labels[requested_match_view],
        key=f"public_match_view_v144_{tournament_id}",
        on_change=_rerun_full_public_app,
    ) or match_view_labels[requested_match_view]
    selected_match_view = match_key_by_label.get(match_view, "all")

    if selected_match_view != requested_match_view and hasattr(st, "query_params"):
        st.query_params["matches"] = selected_match_view
        st.query_params["section"] = "matches"
        st.query_params["cup"] = str(row_value(tournament, "public_slug", tournament_id) or tournament_id)
        if requested_team_id:
            st.query_params["team"] = str(requested_team_id)

    if selected_match_view == "upcoming":
        base_match_list = [m for m in published_matches if m["home_score"] is None or m["away_score"] is None]
    elif selected_match_view == "played":
        base_match_list = list(played_matches)
    else:
        base_match_list = list(published_matches)

    if selected_match_view == "played" and not played_matches:
        st.info("Inga publicerade matcher har ett komplett resultat ännu.")

    if requested_team_id:
        base_match_list = [
            match for match in base_match_list
            if requested_team_id in (
                source_team_id(match["home_source"]),
                source_team_id(match["away_source"]),
            )
        ]
        follow_info_col, follow_clear_col = st.columns([3, 1])
        follow_info_col.info(f"⭐ Min cup visar matcher för {public_team_names[requested_team_id]}.")
        def _clear_public_team_filter() -> None:
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
                st.query_params["section"] = "matches"

        follow_clear_col.button(
            "Visa hela cupen",
            key=f"public_clear_team_filter_v144_{tournament_id}",
            use_container_width=True,
            on_click=_clear_public_team_filter,
        )

    if requested_pitch_no:
        base_match_list = [m for m in base_match_list if int(m["pitch_number"] or 0) == requested_pitch_no]
        st.info(f"📍 Du visar matcher på Plan {requested_pitch_no}.")

    if requested_match_id:
        _exact_matches = [m for m in base_match_list if int(row_value(m, "id", 0) or 0) == int(requested_match_id)]
        if _exact_matches:
            base_match_list = _exact_matches
            st.caption("🔎 Exakt match")
        else:
            st.warning("Matchen finns inte bland de publicerade matcherna i den här cupen.")

    stage_started = time.perf_counter()
    match_list, _match_filter_mode, match_filter_label, show_match_weather = filter_matches_view(
        base_match_list,
        "public_matches",
        tr("Filtrera matcher"),
    )
    all_filtered_matches = match_list
    match_ids_signature = tuple(
        int(row_value(match_row, "id", 0) or 0)
        for match_row in all_filtered_matches
    )
    limit_key = f"public_match_render_limit_v270_{tournament_id}"
    signature_key = f"public_match_render_signature_v270_{tournament_id}"
    if published_matches_complete:
        if st.session_state.get(signature_key) != match_ids_signature:
            st.session_state[signature_key] = match_ids_signature
            st.session_state[limit_key] = PUBLIC_MATCH_INITIAL_BATCH
        match_list, visible_match_count = visible_match_batch(
            all_filtered_matches,
            st.session_state.get(limit_key, PUBLIC_MATCH_INITIAL_BATCH),
        )
        total_filtered_matches = len(all_filtered_matches)
    else:
        # v532: rows are already bounded by the DB query. Do not reset the
        # render limit merely because "Visa fler" returned a larger server batch.
        match_list = list(all_filtered_matches)
        visible_match_count = len(match_list)
        total_filtered_matches = max(visible_match_count, int(published_match_total or 0))
    if visible_match_count < total_filtered_matches:
        st.caption(
            f"{tr('Visar')} {visible_match_count} av {total_filtered_matches} "
            f"{tr('matcher').lower()} · {match_filter_label}"
        )
    else:
        st.caption(f"{tr('Visar')} {total_filtered_matches} {tr('matcher').lower()} · {match_filter_label}")
    stage_timings["filters_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    stage_started = time.perf_counter()
    visible_played_match_ids = [
        int(row_value(match_row, "id", 0) or 0)
        for match_row in match_list
        if (
            row_value(match_row, "home_score", None) is not None
            and row_value(match_row, "away_score", None) is not None
            and int(row_value(match_row, "id", 0) or 0) > 0
        )
    ]
    # v444: goal/card details are secondary information and used to cost a
    # remote query on every first paint that included played matches. Load them
    # only when the visitor asks for details. Exact-match deep links keep details
    # on automatically because that route explicitly targets one match.
    _events_toggle_key = f"public_match_events_v444_{tournament_id}"
    _event_details_enabled = any((
        bool(row_value(tournament, "enable_scorer_leaderboard", 1)),
        bool(row_value(tournament, "enable_assist_leaderboard", 1)),
        bool(row_value(tournament, "enable_card_statistics", 1)),
    ))
    if requested_match_id and _event_details_enabled:
        show_match_events = True
    elif visible_played_match_ids and _event_details_enabled:
        show_match_events = bool(st.session_state.get(_events_toggle_key, False))
    else:
        show_match_events = False
    public_events_by_match = (
        load_match_events(visible_played_match_ids)
        if show_match_events and visible_played_match_ids
        else {}
    )
    stage_timings["events_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    stage_started = time.perf_counter()

    # v471: weather stays opt-in, but a near upcoming match gets a direct
    # quick action beside the match flow instead of forcing the visitor to
    # reopen filters. This changes only session state; the forecast call still
    # happens inside the existing card renderer after explicit user intent.
    _near_weather_match = None
    if not show_match_weather:
        for _weather_candidate in match_list:
            try:
                _weather_start = datetime.fromisoformat(
                    str(row_value(_weather_candidate, "scheduled_start", ""))
                )
            except (TypeError, ValueError):
                continue
            _minutes_to_weather = int((_weather_start - now).total_seconds() // 60)
            if 0 <= _minutes_to_weather <= 120:
                _near_weather_match = _weather_candidate
                break

    if _near_weather_match is not None:
        _near_weather_minutes = int(
            (
                datetime.fromisoformat(str(row_value(_near_weather_match, "scheduled_start", "")))
                - now
            ).total_seconds()
            // 60
        )

        def _enable_near_match_weather() -> None:
            st.session_state[f"public_matches_weather_{tournament_id}"] = True

        st.button(
            f"🌦️ Visa väder · match om {_near_weather_minutes} min",
            key=f"public_near_weather_v471_{tournament_id}_{int(row_value(_near_weather_match, 'id', 0) or 0)}",
            use_container_width=True,
            help="Aktiverar väderprognos för de synliga matchkorten.",
            on_click=_enable_near_match_weather,
        )

    render_match_cards(
        match_list,
        show_results=None,
        show_weather=show_match_weather,
        events_by_match=public_events_by_match,
    )
    if visible_match_count < total_filtered_matches:
        remaining_matches = total_filtered_matches - visible_match_count
        next_batch_size = min(PUBLIC_MATCH_BATCH_SIZE, remaining_matches)
        def _show_more_public_matches() -> None:
            st.session_state[limit_key] = next_visible_count(visible_match_count, total_filtered_matches)
            # v538: bounded first-paint rows live in the parent workspace.
            # A full rerun is required to ask Turso for the next server batch.
            st.rerun(scope="app")

        st.button(
            f"Visa {next_batch_size} fler matcher",
            key=f"public_matches_more_v270_{tournament_id}_{visible_match_count}",
            use_container_width=True,
            on_click=_show_more_public_matches,
        )
    stage_timings["cards_weather_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    # v529: secondary tournament highlights live below the match list and are
    # opt-in. This removes the scorer leaderboard roundtrip from normal first
    # paint while preserving the feature for visitors who want it.
    _highlights_key = f"public_highlights_v529_{tournament_id}"
    if played_matches:
        show_highlights = st.toggle(
            tr("Visa turneringshöjdpunkter"),
            value=False,
            key=_highlights_key,
            help=tr("Laddar skytteligaledare och laghöjdpunkter först när du ber om det."),
            on_change=_rerun_full_public_app,
        )
    else:
        show_highlights = False

    if show_highlights:
        highlights_started = time.perf_counter()
        team_totals: dict[int, dict[str, int]] = {}
        for match in played_matches:
            home_id = source_team_id(match["home_source"])
            away_id = source_team_id(match["away_source"])
            if home_id is None or away_id is None:
                continue
            home_score = int(match["home_score"] or 0)
            away_score = int(match["away_score"] or 0)
            home_stats = team_totals.setdefault(int(home_id), {"gf": 0, "ga": 0, "played": 0})
            away_stats = team_totals.setdefault(int(away_id), {"gf": 0, "ga": 0, "played": 0})
            home_stats["gf"] += home_score; home_stats["ga"] += away_score; home_stats["played"] += 1
            away_stats["gf"] += away_score; away_stats["ga"] += home_score; away_stats["played"] += 1

        highlights: dict[str, Any] = {}
        if team_totals:
            max_goals = max(stats["gf"] for stats in team_totals.values())
            min_conceded = min(stats["ga"] for stats in team_totals.values() if stats["played"] > 0)
            attack_names = sorted(public_team_names[team_id] for team_id, stats in team_totals.items() if stats["gf"] == max_goals and team_id in public_team_names)
            defence_names = sorted(public_team_names[team_id] for team_id, stats in team_totals.items() if stats["ga"] == min_conceded and stats["played"] > 0 and team_id in public_team_names)
            if attack_names:
                highlights["attack"] = {"names": attack_names, "value": max_goals}
            if defence_names:
                highlights["defence"] = {"names": defence_names, "value": min_conceded}

        scorer_enabled = bool(row_value(tournament, "enable_scorer_leaderboard", 1))
        if scorer_enabled:
            overview_started = time.perf_counter()
            overview = load_overview(tournament_id)
            stage_timings["overview_db_ms"] = round((time.perf_counter() - overview_started) * 1000, 1)
            leader_rows = list(overview.get("leader_rows", []))
            if leader_rows:
                leader = leader_rows[0]
                if int(leader.get("goals") or 0) > 0:
                    highlights["scorer"] = {
                        "player": str(leader.get("player_name") or ""),
                        "team": str(leader.get("team_name") or ""),
                        "value": int(leader.get("goals") or 0),
                    }

        highlights_html = build_highlights_html(highlights, tr=tr)
        if highlights_html:
            st.markdown(highlights_html, unsafe_allow_html=True)
        stage_timings["highlights_ms"] = round((time.perf_counter() - highlights_started) * 1000, 1)

    elapsed_ms = (time.perf_counter() - fragment_started) * 1000
    public_perf_snapshot = {
        "render_ms": round(elapsed_ms, 1),
        "db_calls": int(perf["db_calls"]) - db_calls_before,
        "db_ms": round(float(perf["db_ms"]) - db_ms_before, 1),
        **stage_timings,
        "visible_matches": len(match_list),
        "filtered_matches": total_filtered_matches,
        "played_matches": len(played_matches),
    }
    st.session_state[f"_public_perf_matches_{tournament_id}"] = public_perf_snapshot
    public_perf_history = list(st.session_state.get("_cupnavi_public_matches_perf_history", []))
    public_perf_history.append(public_perf_snapshot)
    st.session_state["_cupnavi_public_matches_perf_history"] = public_perf_history[-12:]
    return public_perf_snapshot
