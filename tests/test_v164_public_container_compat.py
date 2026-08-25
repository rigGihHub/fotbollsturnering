from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
RELEASE="2026.08.25-177-ADMIN-OVERVIEW-CLASS-PROGRESS"

def test_public_view_has_no_keyed_streamlit_containers():
    start=APP.index("def render_public_view")
    end=APP.index("def render_match_reporter_view",start)
    public=APP[start:end]
    assert "st.container(key=" not in public
    assert "st.container(border=True, key=" not in public

def test_share_fragment_uses_compatible_plain_containers():
    start=APP.index("def render_public_share_fragment")
    end=APP.index("\n    render_public_share_fragment()",start)
    block=APP[start:end]
    assert "cn-share-toggle-anchor" in block
    assert "cn-share-panel-anchor" in block
    assert "with st.container():" in block
    assert "with st.container(border=True):" in block

def test_release_is_synced():
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in APP
    assert f'APP_VERSION = "{RELEASE}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE
