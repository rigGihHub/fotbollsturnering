from pathlib import Path

from cupnavi_core.public_view_logic import public_navigation_specs

APP = Path("app.py").read_text(encoding="utf-8")
OVERVIEW = Path("cupnavi_core/public_match_overview.py").read_text(encoding="utf-8")


def test_cupinfo_is_leftmost_public_navigation_item():
    specs = public_navigation_specs()
    assert specs[0] == ("Info", "info", "Cupinfo", "Cupinfo")


def test_public_summary_includes_active_visitors():
    assert "def public_match_overview_db_snapshot(" in APP
    assert "tr('Besökare nu')" in OVERVIEW
    assert "session_token<>?" in APP


def test_share_control_moved_below_public_metrics():
    metrics_pos = APP.index("_active_visitors = _overview_db[\"active_visitors\"]")
    share_pos = APP.index("render_public_share_control(tournament_id, tournament)", metrics_pos)
    match_filter_pos = APP.index("requested_match_view =", metrics_pos)
    assert metrics_pos < share_pos < match_filter_pos
    assert "cn-share-inline-anchor" not in APP
