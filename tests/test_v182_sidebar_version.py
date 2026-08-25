from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
def test_sidebar_short_version_is_visible():
    assert 'st.sidebar.caption("Version v.1.183")' in APP
def test_release_version_sync():
    release="2026.08.25-183-BROWSER-SMOKE-FIX"
    assert f'APP_BUILD_VERSION = "{release}"' in APP
    assert f'APP_VERSION = "{release}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==release
