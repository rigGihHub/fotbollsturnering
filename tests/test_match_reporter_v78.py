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
    start = text.index("def render_match_reporter_view(")
    end = text.index("init_db()", start)
    block = text[start:end]
    assert 'tr("CupNavi Score")' in block
    assert 'tr("Matchhändelser")' in block
    assert 'tr("Domarcentral")' in block
    assert 'tr("Offlineutkast")' in block
    assert "ADMIN_NAV_GROUPS" not in block
    assert "update_match_result_if_unchanged" in block
    assert "player_match_stats" in block
    assert "SET referee_id=?" not in block
    assert "Skapa ny turnering" not in block

def test_admin_password_and_reporter_password_are_separate():
    text = app_text()
    assert 'setting("ADMIN_PASSWORD")' in text
    assert 'reporter_password = setting("MATCH_REPORTER_PASSWORD")' in text
    assert 'test_password = setting("TEST_MATCH_REPORTER_PASSWORD") or "123"' in text
