from pathlib import Path

from cupnavi_core.public_view_logic import public_navigation_specs

APP = Path("app.py").read_text(encoding="utf-8")
REPOSITORY = Path("cupnavi_core/public_match_repository.py").read_text(encoding="utf-8")
OVERVIEW = Path("cupnavi_core/public_match_overview.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")


def test_info_is_leftmost_public_navigation_item():
    specs = public_navigation_specs()
    assert specs[0] == ("Info", "info", "Info", "Info")


def test_visitor_snapshot_capability_remains_but_is_not_on_primary_matches_summary():
    assert "def public_match_overview_db_snapshot(" in APP
    assert "session_token<>?" in REPOSITORY
    summary = OVERVIEW[OVERVIEW.index("def build_summary_html"): ]
    assert "Besökare nu" not in summary
    assert "active_visitors" not in summary


def test_share_control_is_in_persistent_public_left_rail():
    assert "render_share_control(tournament_id, tournament)" not in MATCHES
    workspace = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
    assert "with st.sidebar:" in workspace
    assert "render_public_share_control(tournament_id, tournament, in_sidebar=True)" in workspace
    assert "cn-share-inline-anchor" not in APP
