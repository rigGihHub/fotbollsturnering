from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_share_uses_single_popover():
    start=APP.index("def render_public_share_control(")
    end=APP.index('@st.cache_data(show_spinner=False)', start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "render_public_share_fragment" not in block
    assert "cn_share_visible_" not in block
    assert "_share_spacer" not in block

def test_share_has_compact_rail_anchor():
    assert ".cn-share-rail-anchor + div" in APP
    assert "cn-share-rail-label" in APP

def test_follow_control_is_tightened():
    assert "PUBLIC HEADER STRUCTURE FIX V192" in APP
