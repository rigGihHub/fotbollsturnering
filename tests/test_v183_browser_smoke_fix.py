from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SMOKE=(ROOT/"e2e/test_streamlit_browser_smoke.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.31-347-SCHEDULE-READINESS-POLISH"

def test_smoke_test_does_not_wait_for_visible_body():
    assert 'page.wait_for_selector("body",state="attached"' in SMOKE
    assert 'page.wait_for_selector("body",timeout=20000)' not in SMOKE

def test_smoke_waits_for_streamlit_app_root():
    assert 'stAppViewContainer' in SMOKE
    assert 'state="visible"' in SMOKE

def test_sidebar_version_updated():
    assert 'release_ui_label(APP_BUILD_VERSION)' in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
