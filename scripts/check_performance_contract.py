from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
public_workspace=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
public_matches=(ROOT/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
public_team_follow=(ROOT/"cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
repo=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
main=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
match_reporter=(ROOT/"cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
wizard=(ROOT/"cupnavi_core/new_tournament_wizard.py").read_text(encoding="utf-8")
initial_setup=(ROOT/"cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")
performance_module=(ROOT/"cupnavi_core/performance.py").read_text(encoding="utf-8")
assert "def public_core_snapshot" in app
assert "_public_core = public_core_snapshot(" in public_workspace
assert "include_matches=_needs_public_matches" in public_workspace
assert "def public_snapshot" in repo and "with connect() as con:" in repo[repo.index("def public_snapshot"):]
assert "Server-Timing" in main and "X-CupNavi-Process-Ms" in main
assert "on_click=_adjust_quick_score" in match_reporter
assert "on_click=_save_quick_result_callback" in match_reporter
assert "on_click=_set_match_status_callback" in match_reporter
assert "on_click=_clear_public_search" in public_workspace
assert "on_click=_open_public_search_result" in public_workspace
assert "on_click=_clear_public_team_filter" in public_matches
assert "on_click=_show_more_public_matches" in public_matches
assert "on_change=_sync_public_favorite_team" in public_team_follow
assert "on_click=_open_public_team_matches" in public_team_follow
assert "on_click=_clear_public_favorite_team" in public_team_follow
assert "on_click=_open_public_next_match" in public_team_follow
assert "favorite_team_primary_action_label" in public_team_follow
assert "if show_directions:" in public_team_follow
assert "if show_match_events and visible_played_match_ids" in public_matches
assert "def public_scorer_leader_db_snapshot" in app
assert "public_scorer_leader_db_snapshot=public_scorer_leader_db_snapshot" in app
assert "load_overview=public_scorer_leader_db_snapshot" in public_workspace
assert "on_click=_set_wizard_step" in wizard
assert "on_click=_leave_rules_for_step" in initial_setup
assert "on_click=_open_admin_page" in app
assert "_cupnavi_admin_cache_flow_primary_" in app
assert "_cupnavi_admin_cache_sidebar_rules_" in app
assert "_cupnavi_admin_cache_lifecycle_counts_" in app
assert "PERFORMANCE_BUDGETS" in performance_module
for _route in (
    "Turneringsvy/Info",
    "Turneringsvy/Matcher",
    "Turneringsvy/Mitt lag",
    "Admin/Adminöversikt",
    "Admin/Lag",
    "Admin/Grupper",
    "Admin/Skapa och publicera schema",
    "Admin/Kontroller",
):
    assert f'"{_route}"' in performance_module
assert '"Budget": (' in app

# v448: mobile playoff must stay an in-memory presentation pass.
_public_presentation = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()
_mobile_start = _public_presentation.index("def _mobile_status")
_mobile_end = _public_presentation.index("bronze_matches =", _mobile_start)
_mobile_block = _public_presentation[_mobile_start:_mobile_end]
assert "all_rows(" not in _mobile_block, "Mobile playoff must not add DB roundtrips"
assert "one_row(" not in _mobile_block, "Mobile playoff must not add DB roundtrips"
assert "Vinnaren går vidare till" in _mobile_block, "Mobile playoff progression path missing"


# v457: post-freeze performance/mobile QA must not silently regress.
assert 'first_render": {"render_ms": 1800.0, "db_calls": 5}' in performance_module
assert 'warm_rerun": {"render_ms": 850.0, "db_calls": 2}' in performance_module
assert 'warm_rerun": {"render_ms": 1050.0, "db_calls": 3}' in performance_module
_style = (ROOT / "cupnavi_core" / "style_system.py").read_text()
assert '[data-testid="stCheckbox"] label' in _style
assert '[data-testid="stRadio"] label' in _style
assert '.cn-follow-team{font-size:1.22rem;overflow-wrap:anywhere}' in _style

# v458: interaction latency fast paths must stay single-rerun.
assert "on_change=_sync_language_selector" in app
assert app.count("on_click=_set_admin_entry_mode") >= 6
assert "on_click=_open_admin_entry_tournament" in app
_role_codes = (ROOT / "cupnavi_core" / "admin_role_codes_view.py").read_text()
_code_block = _role_codes[_role_codes.index("if create_requested:"):_role_codes.index("if st.session_state.get(code_key):")]
assert "st.rerun()" not in _code_block
# v458: interaction latency
# v459: mobile flow friction must stay presentation-only and compact.
_team_portal = (ROOT / "cupnavi_core" / "team_portal_view.py").read_text()
assert 'with st.expander("Visa hela checklistan", expanded=False):' in _team_portal
assert 'mobile_match_preview(matches, now=datetime.now(), limit=3)' in _team_portal
assert 'with st.expander(f"Visa alla {len(matches)} matcher", expanded=False):' in _team_portal
# v459: mobile flow friction
# v460: reporter mobile density keeps cup-day callbacks and compact shell.
_reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
_style = (ROOT / "cupnavi_core" / "style_system.py").read_text()
assert 'with st.container(key=f"reporter_quick_score_shell_' in _reporter
assert "on_click=_adjust_quick_score" in _reporter
assert "on_click=_save_quick_result_callback" in _reporter
assert "on_click=_reset_quick_score" in _reporter
assert '[class*="st-key-reporter_quick_score_shell_"]' in _style
assert 'flex-wrap:nowrap!important' in _style
# v460: reporter mobile density
# v461: cupday mobile admin density keeps operational pulse first.
assert 'class="cn-day-kpis"' in app
assert "Pågår nu" in app and "Problem" in app and "Nästa 45 min" in app
assert "_primary_risk = _day_readiness[0]" in app
assert 'with st.expander(f"Planer just nu · {len(_day_snapshot[\'pitch_states\'])}", expanded=False):' in app
# v461: cupday mobile admin density
# v462: public first screen keeps latest result in-memory and directions lazy.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
assert 'cn-follow-latest-result' in _follow
assert '_last = favorite_snapshot.get("latest_match")' in _follow
assert "show_directions = st.toggle" in _follow
assert "if show_directions:" in _follow
assert '_visible_upcoming = _upcoming[:3]' in _follow
# v462: public first screen
# v463: public match card density keeps core scan information and no new DB work.
_cards = (ROOT / "cupnavi_core" / "public_match_cards.py").read_text()
assert ".public-match-card{padding:10px!important;margin:7px 0!important" in _cards
assert ".cn-match-context .match-number{display:none!important}" in _cards
assert "referee_label = public_referee_label(match_row)" in _cards
assert "if referee_label else \"\"" in _cards
# v463: public match card density
# v464: mobile compatibility matrix / public navigation robustness.
_style = (ROOT / "cupnavi_core" / "style_system.py").read_text()
assert "@media(max-width:360px)" in _style
assert "@media(max-width:330px)" in _style
assert "top:env(safe-area-inset-top,0px) !important" in _style
assert "-webkit-text-size-adjust:100%!important" in _style
assert 'input,textarea,select,[role="combobox"]{font-size:16px!important}' in _style
assert "min-height:44px!important" in _style
# v464: mobile compatibility matrix
# v466: multi favorites + public pdf stay lazy on public first paint.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
assert 'st.multiselect(' in _follow
assert 'st.query_params["teams"]' in _follow
assert 'row_value(row, "age_class", "")' in _follow
assert '"Skapa och ladda ned PDF"' in app
assert 'data=lambda: _build_public_cup_program_pdf_bytes' in app
assert 'on_click="ignore"' in app
# v466/v494: multi favorites + public pdf stays lazy until the download click.
# v467: multi favorite timeline runs entirely on loaded public matches.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
_helper = (ROOT / "cupnavi_core" / "public_team_follow.py").read_text()
assert "build_multi_favorite_timeline(" in _follow
assert "published_matches," in _follow
assert "proximity_minutes=60" in _follow
assert "def build_multi_favorite_timeline(" in _helper
# v467: multi favorite timeline
# v468: family next step is derived entirely from the existing favorite timeline.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
_helper = (ROOT / "cupnavi_core" / "public_team_follow.py").read_text()
assert "build_family_next_step(" in _follow
assert "def build_family_next_step(" in _helper
assert ">Nästa för familjen<" in _follow
# v468: family next step
# v469: family travel guidance stays lazy and scoped to multi-favorite follow-up.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
_helper = (ROOT / "cupnavi_core" / "public_team_follow.py").read_text()
assert "build_family_travel_guidance(" in _follow
assert "def build_family_travel_guidance(" in _helper
assert 'if _family_step["following_item"] is not None:' in _follow
assert "FROM pitch_travel_times WHERE tournament_id=?" in _follow
# v469: family travel guidance
# v470: weather/scorers/directions are easier to reach without first-paint cost.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
assert '"🌦️ Väder för nästa match"' in _follow
assert '"⚽ Visa målskyttar och kort"' in _follow
assert 'st.session_state[f"public_matches_weather_{tournament_id}"] = True' in _follow
assert "fetch_weather_forecast(" not in _follow
assert "_show_family_directions = st.toggle(" in _follow
# v470: weather scorers directions
# v471: smart match cards keep weather/events opt-in while moving actions closer.
_matches = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text()
_cards = (ROOT / "cupnavi_core" / "public_match_cards.py").read_text()
_present = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()
assert "0 <= _minutes_to_weather <= 120" in _matches
assert '"🌦️ Visa väder · match om' in _matches
assert "fetch_weather_forecast(" not in _matches
assert "cn-match-events-compact" in _present
assert ".cn-match-events-compact{" in _cards
# v471: smart match cards
# v472: public mobile QA keeps secondary actions collapsed and lazy.
_follow = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text()
_matches = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text()
assert 'with st.expander("Mer om senaste resultatet", expanded=False):' in _follow
assert 'with st.expander("Väder & vägbeskrivning", expanded=False):' in _follow
assert "if show_directions:" in _follow
assert "elif visible_played_match_ids and _event_details_enabled:" in _matches
assert "value=True" in _matches
assert "0 <= _minutes_to_weather <= 120" in _matches
# v472: public mobile QA
# v473: table/playoff mobile QA changes presentation only.
_stats = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text()
_present = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()
assert "expanded=True" in _stats
assert "expanded=_bracket_index == 0" in _stats
assert "calculate_all_group_tables(tournament_id, tournament)" in _stats
assert "brackets_for_display(tournament_id)" in _stats
assert ".texttv-table td.team{{font-size:12px!important" in _present
# v473: table playoff mobile QA
# v474: Cupinfo/navigation QA changes hierarchy and visible labels only.
_info = (ROOT / "cupnavi_core" / "public_info_view.py").read_text()
_logic = (ROOT / "cupnavi_core" / "public_view_logic.py").read_text()
assert '("Mitt lag", "team", "Mina lag", "Mina lag")' in _logic
assert "Viktig information från arrangören" in _info
assert 'with st.expander("📘 " + tr("Cupens regler"), expanded=False):' in _info
assert '"Fler cupdetaljer"' in _info
# v474: cupinfo navigation QA
# v475: playoff dependency safety adds write-time guards only.
_app = (ROOT / "app.py").read_text()
_guard = (ROOT / "cupnavi_core" / "playoff_dependency_safety.py").read_text()
assert 'def _playoff_dependency_guard(' in _app
assert 'globals().get("_playoff_dependency_guard")' in _app
assert "transitive_downstream_match_ids(" in _app
assert 'f"winner:{current_id}"' in _guard and 'f"loser:{current_id}"' in _guard
assert "dependency_impact(" in _guard
# v475: playoff dependency safety
# v476: playoff correction guidance is write-path/UI guidance only.
_app = (ROOT / "app.py").read_text()
_schedule = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text()
_guard = (ROOT / "cupnavi_core" / "playoff_dependency_safety.py").read_text()
assert "build_dependency_guidance(" in _guard
assert '"guidance": guidance' in _app
assert "first_dependency_message" in _app
assert 'dependency_blocked = list(save_result.get("dependency_blocked", []))' in _schedule
# v476: playoff correction guidance
# v477: playoff correction recovery is admin write-path only.
_app = (ROOT / "app.py").read_text()
_schedule = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text()
_guard = (ROOT / "cupnavi_core" / "playoff_dependency_safety.py").read_text()
assert "def recovery_eligibility(" in _guard
assert "def _reset_unused_playoff_downstream_match(" in _app
assert "actual_started_at IS NULL" in _app
assert "NOT EXISTS (SELECT 1 FROM player_match_stats" in _app
assert "↩ Återställ oanvänd match" in _schedule
# v477: playoff correction recovery
# v478: playoff chain audit stays on result-correction write paths.
_app = (ROOT / "app.py").read_text()
_guard = (ROOT / "cupnavi_core" / "playoff_dependency_safety.py").read_text()
assert "def transitive_downstream_match_ids(" in _guard
assert "transitive_downstream_match_ids(" in _app
assert "WHERE m.bracket_id=?" in _app
assert 'f"winner:{current_id}"' in _guard
assert 'f"loser:{current_id}"' in _guard
# v478: playoff chain audit
# v479: rehearsal hardening changes go-live controls only.
_app = (ROOT / "app.py").read_text()
_rehearsal = (ROOT / "cupnavi_core" / "sharp_rehearsal.py").read_text()
assert "playoff_dependency" in _rehearsal
assert "playoff_chain" in _rehearsal
assert "playoff_recovery" in _rehearsal
assert "Skarpt genrep · 2–3 mobiler/sessioner" in _app
# v479: sharp rehearsal hardening
# v480: production readiness audit affects config/go-live only.
_app = (ROOT / "app.py").read_text()
_go_live = (ROOT / "cupnavi_core" / "go_live_readiness.py").read_text()
assert "TURSO_CONFIG_PARTIAL" in _app
assert "vägrar använda lokal fallback" in _app
assert "database_config_partial" in _go_live
assert "admin_access_configured" in _go_live
# v480: production readiness audit
# v481: Turso failure recovery affects connection failure paths only.
_app = (ROOT / "app.py").read_text()
assert "def _discard_cloud_raw_connection(" in _app
assert "Skrivningar retryas aldrig" in _app
assert "automat-retrya aldrig commiten" in _app
assert "_new_cloud_raw_connection()" in _app
# v481: Turso failure recovery
# v482: cupday failure UX only wraps write error paths.
_reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
assert "Tryck inte igen direkt" in _reporter
assert "reporter_write_failure_message" in _reporter
assert "_set_write_failure_notice(" in _reporter
# v482: cupday failure UX
# v483: recovery UX adds a manual refresh path after ambiguous writes.
_reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
_app = (ROOT / "app.py").read_text()
assert "🔄 Läs om från servern" in _reporter
assert "reporter_write_failure_context" in _reporter
assert "Ditt försök finns redan sparat" in _reporter
assert "refresh_server_state=_clear_render_query_cache" in _app
# v483: recovery UX
# v484: emergency UI must not add polling or background DB probes.
_app = (ROOT / "app.py").read_text()
assert "🧯 Cupdagens nödpaket" in _app
assert "backup_created_at_" in _app
assert "CupNavi byter inte automatiskt till lokal databas" in _app
# v484: emergency cupday pack
# v486: extreme latency II
_reporter_v486 = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
_app_v486 = (ROOT / "app.py").read_text()
assert _reporter_v486.count("st.rerun()") <= 3
assert "_show_bulk_results = st.toggle(" in _reporter_v486
assert "on_click=_undo_latest_quick_event" in _reporter_v486
assert _app_v486.count("st.rerun()") <= 89
# v487: first paint & DB roundtrip
_app_v487 = (ROOT / "app.py").read_text()
assert "if not include_matches and not include_teams:" in _app_v487
assert "def cupday_boot_db_snapshot" in _app_v487
assert "_day_boot = cupday_boot_db_snapshot" in _app_v487
# v488: Text-TV 330 foundation must remain asset-free and lightweight.
_theme_v488 = (ROOT / "cupnavi_core" / "texttv330_theme.py").read_text()
_app_v488 = (ROOT / "app.py").read_text()
assert "TEXT-TV 330 FUTURE FOUNDATION V488" in _theme_v488
assert "@import" not in _theme_v488
assert "url(" not in _theme_v488
assert "texttv330_public_style_tag()" in _app_v488
assert len(_app_v488.splitlines()) < 16629
# v489: match & result system is CSS-only and asset-free.
_theme_v489 = (ROOT / "cupnavi_core" / "texttv330_theme.py").read_text()
assert "V489 · MATCH & RESULT SYSTEM" in _theme_v489
_v489_block = _theme_v489[_theme_v489.index("V489 · MATCH & RESULT SYSTEM"):]
assert "@import" not in _v489_block
assert "url(" not in _v489_block
assert ".public-match-card.is-live" in _theme_v489
assert ".texttv-table td:nth-child(10)" in _theme_v489
# v491: action queue must reuse existing Cupday data only.
_app_v491 = (ROOT / "app.py").read_text()
assert "# v491: one ranked operational queue" in _app_v491
_v491_start = _app_v491.index("# v491: one ranked operational queue")
_v491_end = _app_v491.index("if _day_readiness:", _v491_start)
_v491_block = _app_v491[_v491_start:_v491_end]
assert "all_rows(" not in _v491_block and "one_row(" not in _v491_block and "db()" not in _v491_block
assert "st.rerun()" not in _v491_block
# v492: callback-first buttons keep the explicit rerun budget lower.
_app_v492 = (ROOT / "app.py").read_text()
assert _app_v492.count("st.rerun()") <= 86
assert "on_click=_open_cupday_delay" in _app_v492
assert "on_click=_open_current_cup_setup" in _app_v492
assert "on_click=_open_focused_team_roster" in _app_v492
print("Performance contract OK")
