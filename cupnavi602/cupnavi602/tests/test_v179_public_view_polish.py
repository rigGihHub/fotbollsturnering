from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
def test_compact_space_and_share_action():
    assert ".cn-mode-nav-safezone{height:24px!important;display:block!important}" in STYLE
    assert 'with st.popover("Dela"' in APP
    assert "render_public_share_fragment" not in APP
