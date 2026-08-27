from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.27-208-PUBLIC-MATCH-PERFORMANCE-REVIEW"

def test_no_production_reporter_123_fallback():
    assert 'reporter_password = setting("MATCH_REPORTER_PASSWORD") or "123"' not in APP
    assert 'test_password = setting("TEST_MATCH_REPORTER_PASSWORD") or "123"' in APP

def test_simple_test_login_is_restricted_to_test_cups():
    assert 'st.session_state["reporter_auth_scope"] = "test_only"' in APP
    assert "COALESCE(environment_type,'production')='test'" in APP

def test_optimistic_result_lock_exists():
    assert "def update_match_result_if_unchanged" in APP
    assert "AND home_score IS ? AND away_score IS ?" in APP
    assert "ändrats av en annan användare" in APP
    assert "_reporter_conflicts" in APP
    assert "reporter_conflict_message" in APP

def test_admin_can_always_delete_real_cup():
    assert "En riktig cup kan alltid raderas. Admin kan göra det även om cupen är publicerad eller har spelade matcher." in APP
    assert "Radera permanent" in APP

def test_version():
    assert "Version v.1.208" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
