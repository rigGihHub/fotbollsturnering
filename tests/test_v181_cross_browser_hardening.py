from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
CSS=(ROOT/"public_pwa/styles.css").read_text(encoding="utf-8")
WF=(ROOT/".github/workflows/cross-browser.yml").read_text(encoding="utf-8")
R="2026.08.25-184-STREAMLIT-SMOKE-SEMANTICS"

def test_webkit_backdrop_prefixes_exist():
    assert "-webkit-backdrop-filter:blur(8px)" in APP
    assert "-webkit-backdrop-filter:blur(6px)" in APP
    assert "-webkit-backdrop-filter:blur(12px)" in CSS

def test_modern_mobile_viewport_has_fallback():
    assert "min-height:100vh; min-height:100dvh" in APP
    assert "min-height:100%;min-height:100dvh" in CSS

def test_touch_and_ios_safe_area_hardening():
    assert "touch-action:manipulation" in APP
    assert "-webkit-overflow-scrolling:touch" in APP
    assert "env(safe-area-inset-bottom)" in CSS

def test_ci_covers_all_three_browser_engines():
    assert "chromium firefox webkit" in WF
    assert "test_cross_browser_matrix.py" in WF
    assert "test_streamlit_browser_smoke.py" in WF

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
