from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
from typing import Any, Callable


@dataclass(frozen=True)
class PublicWorkspaceDependencies:
    st: Any
    perf: Any
    derived_cache_get: Callable[..., Any]
    row_value: Callable[..., Any]
    all_rows: Callable[..., Any]
    build_public_hero_html: Callable[..., str]
    build_public_navigation_html: Callable[..., str]
    calculate_all_group_tables: Callable[..., Any]
    calculate_table: Callable[..., Any]
    confirm_notification_subscription: Callable[..., bool]
    create_notification_subscription: Callable[..., Any]
    cup_date_label: Callable[..., str]
    fetch_weather_forecast: Callable[..., Any]
    filter_matches: Callable[..., Any]
    inject_public_experience_styles: Callable[..., Any]
    kit_background_for_team: Callable[..., Any]
    match_duration_minutes: Callable[..., Any]
    match_kit_colors: Callable[..., Any]
    normalize_status: Callable[..., Any]
    one_row: Callable[..., Any]
    pitch_label: Callable[..., str]
    public_core_snapshot: Callable[..., Any]
    public_cup_url: Callable[..., str]
    public_match_events_db_snapshot: Callable[..., Any]
    public_match_events_html: Callable[..., str]
    public_match_overview_db_snapshot: Callable[..., Any]
    public_navigation_specs: Callable[..., Any]
    render_empty_state: Callable[..., Any]
    render_public_info_section: Callable[..., Any]
    render_public_match_cards_module: Callable[..., Any]
    render_public_match_filters_module: Callable[..., Any]
    render_public_matches_fragment_module: Callable[..., Any]
    render_public_screen_mode: Callable[..., Any]
    render_public_share_control: Callable[..., Any]
    render_public_statistics_section: Callable[..., Any]
    render_public_team_follow: Callable[..., Any]
    resolve_public_page: Callable[..., str]
    resolve_source: Callable[..., Any]
    sort_public_matches: Callable[..., Any]
    source_label: Callable[..., str]
    sport_profile: Callable[..., Any]
    swedish_datetime: Callable[..., Any]
    tr: Callable[..., str]
    track_public_visit: Callable[..., Any]
    unsubscribe_notification_subscription: Callable[..., bool]
    weather_for_match: Callable[..., Any]
    weather_label: Callable[..., Any]


def render_public_workspace(tournament_id: int, tournament: Any, deps: PublicWorkspaceDependencies) -> None:
    """Render the public tournament workspace while keeping app-owned services injected."""
    st = deps.st
    _PERF = deps.perf
    _derived_cache_get = deps.derived_cache_get
    _row_value = deps.row_value
    all_rows = deps.all_rows
    build_public_hero_html = deps.build_public_hero_html
    build_public_navigation_html = deps.build_public_navigation_html
    calculate_all_group_tables = deps.calculate_all_group_tables
    calculate_table = deps.calculate_table
    confirm_notification_subscription = deps.confirm_notification_subscription
    create_notification_subscription = deps.create_notification_subscription
    cup_date_label = deps.cup_date_label
    fetch_weather_forecast = deps.fetch_weather_forecast
    filter_matches = deps.filter_matches
    inject_public_experience_styles = deps.inject_public_experience_styles
    kit_background_for_team = deps.kit_background_for_team
    match_duration_minutes = deps.match_duration_minutes
    match_kit_colors = deps.match_kit_colors
    normalize_status = deps.normalize_status
    one_row = deps.one_row
    pitch_label = deps.pitch_label
    public_core_snapshot = deps.public_core_snapshot
    public_cup_url = deps.public_cup_url
    public_match_events_db_snapshot = deps.public_match_events_db_snapshot
    public_match_events_html = deps.public_match_events_html
    public_match_overview_db_snapshot = deps.public_match_overview_db_snapshot
    public_navigation_specs = deps.public_navigation_specs
    render_empty_state = deps.render_empty_state
    render_public_info_section = deps.render_public_info_section
    render_public_match_cards_module = deps.render_public_match_cards_module
    render_public_match_filters_module = deps.render_public_match_filters_module
    render_public_matches_fragment_module = deps.render_public_matches_fragment_module
    render_public_screen_mode = deps.render_public_screen_mode
    render_public_share_control = deps.render_public_share_control
    render_public_statistics_section = deps.render_public_statistics_section
    render_public_team_follow = deps.render_public_team_follow
    resolve_public_page = deps.resolve_public_page
    resolve_source = deps.resolve_source
    sort_public_matches = deps.sort_public_matches
    source_label = deps.source_label
    sport_profile = deps.sport_profile
    swedish_datetime = deps.swedish_datetime
    tr = deps.tr
    track_public_visit = deps.track_public_visit
    unsubscribe_notification_subscription = deps.unsubscribe_notification_subscription
    weather_for_match = deps.weather_for_match
    weather_label = deps.weather_label

    # Besöksstatistik registreras sist så den inte ligger före sidans innehåll.
    if hasattr(st, "query_params"):
        _confirm_token = str(st.query_params.get("notify_confirm", "") or "").strip()
        _unsubscribe_token = str(st.query_params.get("notify_unsubscribe", "") or "").strip()
        if _confirm_token:
            st.success("✓ E-postnotiser är aktiverade.") if confirm_notification_subscription(_confirm_token) else st.warning("Bekräftelselänken är ogiltig eller redan använd.")
            try:
                del st.query_params["notify_confirm"]
            except KeyError:
                pass
        if _unsubscribe_token:
            st.success("E-postnotiser är avslutade.") if unsubscribe_notification_subscription(_unsubscribe_token) else st.warning("Avregistreringslänken är ogiltig eller redan använd.")
            try:
                del st.query_params["notify_unsubscribe"]
            except KeyError:
                pass
    _public_core = public_core_snapshot(tournament_id)
    published_matches = _public_core["matches"]
    played_matches = [m for m in published_matches if m["home_score"] is not None and m["away_score"] is not None]
    public_teams = _public_core["teams"]
    public_team_by_id = {row["id"]: row for row in public_teams}
    public_team_names = {row["id"]: row["name"] for row in public_teams}
    now = datetime.now()

    def _public_pitch_label(match_row):
        return str(_row_value(match_row, "pitch_name", None) or pitch_label(tournament_id, match_row["pitch_number"]))

    def _public_referee_label(match_row):
        return str(_row_value(match_row, "referee_name", "") or "")

    # Grupper laddas först när skärm, gruppfilter eller statistik behöver dem.
    def _load_public_groups():
        return _derived_cache_get(
            ("public-groups", int(tournament_id)),
            lambda: all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,)),
        )

    def _public_source_team_id(source):
        """Lös vanliga team:<id>-källor lokalt; bara komplexa slutspelskällor behöver DB-resolver."""
        parts = source.split(":") if source else []
        if len(parts) >= 2 and parts[0] == "team":
            try:
                return int(parts[1])
            except (TypeError, ValueError):
                return None
        return resolve_source(source)

    def _public_source_label(source):
        team_id = _public_source_team_id(source)
        if team_id in public_team_names:
            return public_team_names[team_id]
        return source_label(source)

    screen_mode = bool(hasattr(st, "query_params") and str(st.query_params.get("screen", "")) == "1")
    if screen_mode:
        render_public_screen_mode(
            tournament_id,
            tournament,
            published_matches,
            now=now,
            public_cup_url=public_cup_url,
            source_label=_public_source_label,
            pitch_label=_public_pitch_label,
            match_duration_minutes=match_duration_minutes,
            calculate_all_group_tables=calculate_all_group_tables,
            all_rows=all_rows,
        )
        return
    filtered_public_matches = published_matches
    next_match = next(
        (
            m for m in filtered_public_matches
            if datetime.fromisoformat(m["scheduled_start"]) >= now and m["home_score"] is None
        ),
        None,
    )
    # Keep eager next-match calculation for parity with the existing public workspace contract.
    _ = next_match
    public_lifecycle = normalize_status(
        _row_value(tournament, "lifecycle_status", None),
        is_published=bool(tournament["is_published"]),
    )
    st.markdown(
        build_public_hero_html(
            tournament,
            lifecycle_status=public_lifecycle,
            cup_date_label=cup_date_label,
            row_value=_row_value,
            translate=tr,
        ),
        unsafe_allow_html=True,
    )

    team_query = st.query_params.get("team") if hasattr(st, "query_params") else None
    pitch_query = st.query_params.get("pitch") if hasattr(st, "query_params") else None
    try:
        requested_team_id = int(team_query) if team_query else None
    except (TypeError, ValueError):
        requested_team_id = None
    try:
        requested_pitch_no = int(pitch_query) if pitch_query else None
    except (TypeError, ValueError):
        requested_pitch_no = None
    if requested_team_id not in public_team_names:
        requested_team_id = None

    inject_public_experience_styles(st)

    render_public_team_follow(
        tournament_id=tournament_id,
        tournament=tournament,
        requested_team_id=requested_team_id,
        public_teams=public_teams,
        public_team_names=public_team_names,
        published_matches=published_matches,
        now=now,
        tr=tr,
        source_team_id=_public_source_team_id,
        source_label=_public_source_label,
        row_value=_row_value,
        public_pitch_label=_public_pitch_label,
        pitch_label=pitch_label,
        swedish_datetime=swedish_datetime,
        calculate_table=calculate_table,
        one_row=one_row,
        all_rows=all_rows,
        create_notification_subscription=create_notification_subscription,
    )

    public_page_key = f"public_page_v167_{tournament_id}"
    requested_section = str(st.query_params.get("section", "")) if hasattr(st, "query_params") else ""
    public_page = resolve_public_page(requested_section, st.session_state.get(public_page_key))
    st.session_state[public_page_key] = public_page
    st.session_state["_cupnavi_current_public_page"] = public_page

    st.markdown(
        build_public_navigation_html(
            public_navigation_specs(),
            current_page=public_page,
            public_slug=_row_value(tournament, "public_slug", tournament_id) or tournament_id,
            requested_team_id=requested_team_id,
            translate=tr,
        ),
        unsafe_allow_html=True,
    )

    screen_url = public_cup_url(tournament_id) + ("&" if "?" in public_cup_url(tournament_id) else "?") + "screen=1"
    if public_page == "Info":
        st.markdown(
            f"<div style='text-align:right;margin:-4px 0 8px'><a class='cn-screen-link' href='{html.escape(screen_url, quote=True)}'>🖥 Informationsskärm</a></div>",
            unsafe_allow_html=True,
        )

    def _filter_public_matches(base_matches, key_prefix, heading):
        return render_public_match_filters_module(
            base_matches,
            key_prefix,
            heading,
            tournament_id=tournament_id,
            tr=tr,
            public_teams=public_teams,
            public_team_names=public_team_names,
            load_public_groups=_load_public_groups,
            source_team_id=_public_source_team_id,
            row_value=_row_value,
            filter_matches=filter_matches,
            sort_public_matches=sort_public_matches,
        )

    def _render_public_match_cards(matches, show_results=None, show_weather=False, events_by_match=None):
        return render_public_match_cards_module(
            matches,
            tournament=tournament,
            show_results=show_results,
            show_weather=show_weather,
            events_by_match=events_by_match,
            row_value=_row_value,
            fetch_weather_forecast=fetch_weather_forecast,
            public_team_by_id=public_team_by_id,
            public_team_names=public_team_names,
            public_source_team_id=_public_source_team_id,
            public_source_label=_public_source_label,
            swedish_datetime=swedish_datetime,
            weather_for_match=weather_for_match,
            weather_label=weather_label,
            match_kit_colors=match_kit_colors,
            kit_background_for_team=kit_background_for_team,
            public_match_events_html=public_match_events_html,
            public_pitch_label=_public_pitch_label,
            public_referee_label=_public_referee_label,
            render_empty_state=render_empty_state,
            now=now,
        )

    if public_page == "Matcher":
        @st.fragment
        def render_public_matches_fragment():
            return render_public_matches_fragment_module(
                st=st,
                tournament_id=tournament_id,
                tournament=tournament,
                published_matches=published_matches,
                played_matches=played_matches,
                public_teams=public_teams,
                public_team_names=public_team_names,
                requested_team_id=requested_team_id,
                requested_pitch_no=requested_pitch_no,
                now=now,
                perf=_PERF,
                tr=tr,
                row_value=_row_value,
                sport_profile=sport_profile,
                match_duration_minutes=match_duration_minutes,
                source_label=_public_source_label,
                source_team_id=_public_source_team_id,
                pitch_label=_public_pitch_label,
                overview_snapshot=public_match_overview_db_snapshot,
                render_share_control=render_public_share_control,
                filter_matches_view=_filter_public_matches,
                render_match_cards=_render_public_match_cards,
                load_match_events=public_match_events_db_snapshot,
            )

        render_public_matches_fragment()

    if public_page == "Tabeller":
        render_public_statistics_section(tournament_id, tournament, published_matches, played_matches, forced_section=tr("Tabeller"))
    if public_page == "Slutspel":
        render_public_statistics_section(tournament_id, tournament, published_matches, played_matches, forced_section=tr("Slutspel"))
    if public_page == "Statistik":
        render_public_statistics_section(tournament_id, tournament, published_matches, played_matches, forced_section=tr("Topplistor"))
    if public_page == "Info":
        render_public_info_section(tournament_id, tournament, published_matches)

    # Icke-kritisk analytics sist: ett långsamt Turso-write ska inte fördröja innehållet.
    track_public_visit(tournament_id)
