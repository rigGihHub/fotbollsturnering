from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
RELEASE="2026.08.26-198-VISUAL-SYSTEM-CONSOLIDATION"

def test_public_follow_container_uses_compatible_streamlit_api():
    assert 'with st.container():' in APP
    assert 'st.container(key=f"public_follow_{tournament_id}")' not in APP

def test_release_is_synced():
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in APP
    assert f'APP_VERSION = "{RELEASE}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE
