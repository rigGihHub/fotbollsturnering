from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_compact_space_and_share_action():
    assert ".cn-mode-nav-safezone{height:24px!important;display:block!important}" in APP
    assert "_share_spacer, _share_action = st.columns([8, 1])" in APP
    assert "margin:-58px" not in APP
