from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_share_uses_single_popover():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index('# v143: mobil först', start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "render_public_share_fragment" not in block
    assert "cn_share_visible_" not in block
    assert "_share_spacer" not in block

def test_share_is_integrated_with_hero():
    assert ".cn-share-inline-anchor + div" in APP
    assert "margin:-40px 12px 6px auto!important" in APP

def test_follow_control_is_tightened():
    assert "PUBLIC HEADER STRUCTURE FIX V192" in APP
