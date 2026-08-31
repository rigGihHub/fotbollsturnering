from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
INFO=(ROOT/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
MIG=(ROOT/"cupnavi_core/migrations.py").read_text(encoding="utf-8")
WF=(ROOT/".github/workflows/cross-browser.yml").read_text(encoding="utf-8")
R="2026.08.31-349-BEGINNER-FIRST-RUN"

def test_server_side_rate_limits_cover_login_and_feedback():
    assert '_rate_allowed("admin-login", 8, 600)' in APP
    assert 'f"reporter-login:{int(reporter_tid)}"' in APP
    assert 'rate_allowed(f"feedback:{int(tournament_id)}", 5, 600)' in INFO
    assert "rate_allowed=_rate_allowed" in APP
    assert "rå IP lagras aldrig" in APP

def test_rate_limit_schema_is_migrated():
    assert "LATEST_SCHEMA_VERSION = " in MIG
    assert "server_side_rate_limits_v190" in MIG
    assert "CREATE TABLE IF NOT EXISTS rate_limits" in MIG

def test_critical_browser_journey_is_in_ci():
    assert "test_streamlit_critical_journey.py" in WF
    journey=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")
    for browser in ("chromium","firefox","webkit"):
        assert browser in journey
    assert "TESTMILJÖ" in journey
    assert "endast testmiljöer" in journey

def test_testable_database_path_keeps_default():
    assert 'os.getenv("CUPNAVI_DB_PATH") or Path(__file__).with_name("turnering.db")' in APP

def test_version():
    assert "release_ui_label(APP_BUILD_VERSION)" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
