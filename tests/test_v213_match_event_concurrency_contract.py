
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
ADMIN_EVENTS=(ROOT/"cupnavi_core/admin_match_events_view.py").read_text(encoding="utf-8")


def test_both_user_event_flows_use_conditional_write():
    assert APP.count("update_player_match_stats_if_unchanged(") >= 3


def test_conflict_feedback_exists_for_reporter_and_admin():
    assert "reporter_event_conflict_" in WORKSPACE
    assert "event_autosave_conflict_" in ADMIN_EVENTS
    assert "skrevs inte över" in APP + WORKSPACE + ADMIN_EVENTS


def test_unrestricted_demo_upsert_is_not_confused_with_user_flows():
    # Demo generation may still use an unrestricted UPSERT; user-facing
    # Matchrapportör/Admin event autosave must route through the conditional helper.
    reporter_start=APP.index("def _reporter_save_event_rows")
    admin_start=APP.index('if admin_page == "Matchhändelser"')
    reporter=APP[reporter_start:admin_start]
    assert "update_player_match_stats_if_unchanged(" in reporter
    assert "update_player_match_stats_if_unchanged(" not in WORKSPACE

    admin_end=APP.index('if admin_page == "Besöksstatistik"',admin_start)
    admin=APP[admin_start:admin_end]
    assert "update_player_match_stats_if_unchanged(" in admin
    assert "update_player_match_stats_if_unchanged(" not in ADMIN_EVENTS
