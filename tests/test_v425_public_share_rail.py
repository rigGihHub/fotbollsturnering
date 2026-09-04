from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v425_share_is_persistent_left_rail_action():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert "with st.sidebar:" in WORKSPACE
    assert "render_public_share_control(tournament_id, tournament, in_sidebar=True)" in WORKSPACE
    assert "render_share_control(tournament_id, tournament)" not in MATCHES


def test_v425_share_control_has_polished_rail_contract():
    assert "def render_public_share_control(tournament_id, tournament, *, in_sidebar=False):" in APP
    assert "cn-share-rail-label" in APP
    assert 'st.popover("Dela"' in APP
    assert "use_container_width=bool(in_sidebar)" in APP
