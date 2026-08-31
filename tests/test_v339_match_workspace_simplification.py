from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
RESULTS_VIEW = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text(encoding="utf-8")
VERSION = "2026.08.31-347-SCHEDULE-READINESS-POLISH"


def test_release_version_is_v339():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_global_match_navigation_only_exposes_three_core_destinations():
    nav = APP[APP.index("ADMIN_NAV_GROUPS = ["):APP.index("ADMIN_NAV = [")]
    match_line = next(line for line in nav.splitlines() if '("Matcher",' in line)
    assert '("Skapa och publicera schema", tr("Schema"))' in match_line
    assert '("Matcher och resultat", "Resultat")' in match_line
    assert '("Slutspel", tr("Slutspel"))' in match_line
    assert '"Matchhändelser"' not in match_line
    assert '"Tabeller"' not in match_line
    assert '"Skytteligor"' not in match_line


def test_hidden_match_tools_stay_in_match_group():
    assert 'if page in {"Matchhändelser", "Tabeller", "Skytteligor"}:' in APP
    assert 'return "Matcher"' in APP


def test_result_workspace_owns_contextual_event_and_statistics_tools():
    assert 'with st.expander("Fler resultatverktyg", expanded=False):' in RESULTS_VIEW
    assert '"Detaljerade matchhändelser"' in RESULTS_VIEW
    assert 'args=("Matchhändelser",)' in RESULTS_VIEW
    assert '"Tabeller & topplistor"' in RESULTS_VIEW
    assert 'args=("Tabeller",)' in RESULTS_VIEW


def test_contextual_tools_have_clear_return_path_and_existing_workspaces_remain():
    assert APP.count('"← Till Resultat"') >= 3
    assert 'if admin_page == "Matchhändelser":' in APP
    assert 'if admin_page == "Tabeller":' in APP
    assert 'if admin_page == "Skytteligor":' in APP
    assert 'render_admin_match_events_workspace(' in APP


def test_result_integrity_paths_remain_unchanged():
    assert 'update_match_result_if_unchanged(' in APP
    assert 'update_player_match_stats_if_unchanged(' in APP
    assert 'enqueue_goal_push_events(' in APP
