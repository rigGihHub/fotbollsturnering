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


def test_share_control_remains_below_compact_public_metrics():
    summary_pos = MATCHES.index("summary_html = build_summary_html(")
    share_pos = MATCHES.index("render_share_control(tournament_id, tournament)", summary_pos)
    match_filter_pos = MATCHES.index("requested_match_view =", summary_pos)
    assert summary_pos < share_pos < match_filter_pos
    assert "cn-share-inline-anchor" not in APP
