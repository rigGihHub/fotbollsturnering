from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_compact_space_and_share_action():
    assert ".cn-mode-nav-safezone{height:24px!important;display:block!important}" in APP
    assert 'with st.popover("Dela"' in APP
    assert "render_public_share_fragment" not in APP
