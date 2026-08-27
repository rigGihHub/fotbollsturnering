from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SMOKE=(ROOT/"e2e/test_streamlit_browser_smoke.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.27-234-E2E-FRESH-DB-STATE"
def test_smoke_does_not_depend_on_exact_product_copy():
    assert 'any(token in body for token in' not in SMOKE
def test_smoke_verifies_visible_streamlit_root():
    assert 'assert app_root.is_visible()' in SMOKE
def test_sidebar_version():
    assert "Version v.1.234" in APP
def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
