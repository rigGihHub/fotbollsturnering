"""Public match-list orchestration extracted from the Streamlit entrypoint.

The function in this module owns the public Matches page rendering flow, while
app.py remains responsible for the Streamlit fragment boundary and application
services such as DB instrumentation, translation and URL/share helpers.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Sequence

from cupnavi_core.public_highlights import competition_highlights, snapshot_table_bundle
from cupnavi_core.public_match_feed_logic import classify_public_match_feed, public_match_feed_summary
from cupnavi_core.public_match_overview import build_live_feed_html, build_highlights_html, build_summary_html
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
    played_matches: Sequence[Any],
    public_teams: Sequence[Any],
    public_team_names: Mapping[int, str],
    requested_team_id: int | None,
    requested_pitch_no: int | None,
    now: Any,
    perf: Mapping[str, Any],
    tr: Callable[[str], str],
    row_value: Callable[..., Any],
    sport_profile: Callable[[str], Mapping[str, Any]],
    match_duration_minutes: Callable[[Any], int],
    source_label: Callable[[str], str],
    source_team_id: Callable[[str], int | None],
    pitch_label: Callable[[Any], str],
    overview_snapshot: Callable[..., Mapping[str, Any]],
    render_share_control: Callable[[int, Any], Any],
    filter_matches_view: Callable[[Sequence[Any], str, str], tuple[Any, Any, str]],
    render_match_cards: Callable[..., Any],
    load_match_events: Callable[[Sequence[int]], Mapping[int, Sequence[Any]]],
) -> dict[str, Any]:
    """Render the public Matches page and return its measured performance snapshot."""
    fragment_started = time.perf_counter()
    db_calls_before = int(perf["db_calls"])
    db_ms_before = float(perf["db_ms"])

    team_count = len(public_teams)
    total_goals = sum(
        int(match["home_score"] or 0) + int(match["away_score"] or 0)
        for match in played_matches
    )
    stage_timings: dict[str, float] = {}

    stage_started = time.perf_counter()
    live_now, next_matches, recent_results = classify_public_match_feed(
        published_matches,
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

    stage_started = time.perf_counter()
    scorer_enabled = bool(row_value(tournament, "enable_scorer_leaderboard", 1))
    assist_enabled = bool(row_value(tournament, "enable_assist_leaderboard", 1))
    overview_db = overview_snapshot(
        tournament_id,
        scorer_enabled=bool(played_matches) and scorer_enabled,
        assist_enabled=bool(played_matches) and assist_enabled,
    )
    leader_rows = overview_db["leader_rows"]
    active_visitors = overview_db["active_visitors"]
    stage_timings["overview_db_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    stage_started = time.perf_counter()
    highlight_tables = snapshot_table_bundle(
        public_teams,
        published_matches,
        points_win=int(row_value(tournament, "points_win", 3) or 0),
        points_draw=int(row_value(tournament, "points_draw", 1) or 0),
        points_loss=int(row_value(tournament, "points_loss", 0) or 0),
        table_tiebreak=str(row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
    )
    highlights = competition_highlights(
        highlight_tables,
        leader_rows,
        scorer_enabled=scorer_enabled,
        assist_enabled=assist_enabled,
    )
    highlights_html = build_highlights_html(highlights, tr=tr)
    stage_timings["highlights_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)
    # Compatibility field retained from the original profiler contract.
    stage_timings["visitors_ms"] = 0.0

    stage_started = time.perf_counter()
    summary_html = build_summary_html(
        team_count=team_count,
        played_count=len(played_matches),
        total_matches=len(published_matches),
        total_score=total_goals,
        score_label=sport_profile(row_value(tournament, "sport", "Fotboll"))["score_label"],
        active_visitors=active_visitors,
        highlights_html=highlights_html,
        tr=tr,
    )
    st.markdown(summary_html, unsafe_allow_html=True)
    render_share_control(tournament_id, tournament)
    stage_timings["summary_share_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

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
        if follow_clear_col.button(
            "Visa hela cupen",
            key=f"public_clear_team_filter_v144_{tournament_id}",
            use_container_width=True,
        ):
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
                st.query_params["section"] = "matches"
            st.rerun()

    if requested_pitch_no:
        base_match_list = [m for m in base_match_list if int(m["pitch_number"] or 0) == requested_pitch_no]
        st.info(f"📍 QR-länken visar Plan {requested_pitch_no}.")

    stage_started = time.perf_counter()
    match_list, _match_filter_mode, match_filter_label = filter_matches_view(
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
    if st.session_state.get(signature_key) != match_ids_signature:
        st.session_state[signature_key] = match_ids_signature
        st.session_state[limit_key] = PUBLIC_MATCH_INITIAL_BATCH

    match_list, visible_match_count = visible_match_batch(
        all_filtered_matches,
        st.session_state.get(limit_key, PUBLIC_MATCH_INITIAL_BATCH),
    )
    total_filtered_matches = len(all_filtered_matches)
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
    public_events_by_match = load_match_events(visible_played_match_ids) if visible_played_match_ids else {}
    stage_timings["events_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

    stage_started = time.perf_counter()
    show_match_weather = st.toggle(
        "🌦️ " + tr("Visa väderprognos"),
        value=False,
        key=f"public_matches_weather_{tournament_id}",
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
        if st.button(
            f"Visa {next_batch_size} fler matcher",
            key=f"public_matches_more_v270_{tournament_id}_{visible_match_count}",
            use_container_width=True,
        ):
            st.session_state[limit_key] = next_visible_count(visible_match_count, total_filtered_matches)
            st.rerun(scope="fragment")
    stage_timings["cards_weather_ms"] = round((time.perf_counter() - stage_started) * 1000, 1)

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
