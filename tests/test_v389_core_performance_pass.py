from pathlib import Path

RELEASE = "2026.09.03-427-TRAVEL-RULES-FLOW"


def test_v389_batches_schedule_match_events_and_reuses_match_snapshot():
    source = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
    assert "scheduled_matches = adjustable_matches" in source
    assert "event_rows_by_match" in source
    assert "WHERE matches.tournament_id=?" in source
    assert 'WHERE player_match_stats.match_id=? ORDER BY players.name' not in source


def test_v389_release_is_pinned():
    assert Path("VERSION.txt").read_text(encoding="utf-8").strip() == RELEASE
