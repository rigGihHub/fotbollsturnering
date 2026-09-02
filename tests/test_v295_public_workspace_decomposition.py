from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_and_public_workspace_boundary():
    assert VERSION == "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"
    assert "from cupnavi_core.public_workspace_view import PublicWorkspaceDependencies, render_public_workspace" in APP
    start = APP.index("def render_public_view(")
    end = APP.index("def _reporter_save_quick_result", start)
    adapter = APP[start:end]
    assert "render_public_workspace(" in adapter
    assert "PublicWorkspaceDependencies(" in adapter
    assert 'if public_page == "Matcher":' not in adapter
    assert len(adapter.splitlines()) < 80


def test_workspace_owns_public_orchestration_without_database_connection_ownership():
    assert 'if public_page == "Matcher":' in WORKSPACE
    assert 'if public_page == "Tabeller":' in WORKSPACE
    assert 'if public_page == "Slutspel":' in WORKSPACE
    assert 'if public_page == "Mitt lag":' in WORKSPACE
    assert 'if public_page == "Statistik":' not in WORKSPACE
    assert 'if public_page == "Info":' in WORKSPACE
    assert "track_public_visit(tournament_id)" in WORKSPACE
    assert "with db()" not in WORKSPACE
    assert ".commit(" not in WORKSPACE
    assert "UPDATE " not in WORKSPACE
    assert "INSERT INTO" not in WORKSPACE
    assert "DELETE FROM" not in WORKSPACE


def test_public_navigation_and_match_rendering_stay_in_outer_fragment_workspace():
    assert "public_page = resolve_public_page(" in WORKSPACE
    assert "st.segmented_control(" in WORKSPACE
    assert "@st.fragment\ndef render_public_view" in APP
    assert "render_public_matches_fragment_module(" in WORKSPACE
    assert WORKSPACE.index("public_page = resolve_public_page(") < WORKSPACE.index('if public_page == "Matcher":')


def test_public_core_snapshot_remains_injected_from_application_boundary():
    assert "public_core_snapshot=public_core_snapshot" in APP
    assert "public_match_events_db_snapshot=public_match_events_db_snapshot" in APP
    assert "public_match_overview_db_snapshot=public_match_overview_db_snapshot" in APP
    assert "confirm_notification_subscription=confirm_notification_subscription" in APP
    assert "create_notification_subscription=create_notification_subscription" in APP
    assert "unsubscribe_notification_subscription=unsubscribe_notification_subscription" in APP
