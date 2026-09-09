from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_matchcenter_removed_from_public_ui():
    text = app_text()
    assert '"Matchcenter"' not in text
    assert "matchcenter_tab" not in text
    assert "public_matchcenter_" not in text

def test_match_reporter_is_separate_mode():
    text = app_text()
    assert '"Matchrapportör"' in text
    assert "def require_match_reporter_access():" in text
    assert 'reporter_password = setting("MATCH_REPORTER_PASSWORD")' in text
    assert 'test_password = setting("TEST_MATCH_REPORTER_PASSWORD") or "123"' in text
    assert "reporter_authenticated" in text

def test_match_reporter_stops_before_admin_navigation():
    text = app_text()
    assert 'if view_mode == "Matchrapportör":' in text
    assert '_render_with_friendly_error(render_match_reporter_view, tid, tournament)' in text

def test_match_reporter_stays_in_restricted_operational_workspace():
    text = app_text()
    workspace = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
    assert 'deps.translate("CupNavi Score")' in workspace
    assert 'deps.translate("Matchhändelser")' in workspace
    assert 'deps.translate("Domarcentral")' in workspace
    assert 'deps.translate("Offlineutkast")' in workspace
    assert "ADMIN_NAV_GROUPS" not in workspace
    assert "save_quick_result" in workspace
    assert "fetch_player_match_stats" in workspace
    assert "SET referee_id=?" not in workspace
    assert "Skapa ny turnering" not in workspace
    assert "update_match_result_if_unchanged" in text

def test_admin_password_and_reporter_password_are_separate():
    text = app_text()
    assert 'setting("ADMIN_PASSWORD")' in text
    assert 'reporter_password = setting("MATCH_REPORTER_PASSWORD")' in text
    assert 'test_password = setting("TEST_MATCH_REPORTER_PASSWORD") or "123"' in text
