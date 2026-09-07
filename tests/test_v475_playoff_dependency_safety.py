from pathlib import Path

from cupnavi_core.playoff_dependency_safety import dependency_impact, winner_side

VERSION = "2026.09.07-497-MY-TEAMS-NOTICES-POLISH"
APP = Path("app.py").read_text(encoding="utf-8")


def _value(row, key, default=None):
    return row.get(key, default)


def test_version_is_v475():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_same_winner_side_is_not_blocked():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="home",
        downstream_rows=[{"id": 20, "match_status": "finished", "home_score": 2, "away_score": 1, "event_count": 1}],
        row_value=_value,
    )
    assert impact.blocked is False


def test_changed_winner_allowed_when_downstream_untouched():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="away",
        downstream_rows=[{"id": 20, "match_status": "not_started", "home_score": None, "away_score": None, "event_count": 0}],
        row_value=_value,
    )
    assert impact.blocked is False


def test_changed_winner_blocked_when_downstream_started():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="away",
        downstream_rows=[{"id": 20, "match_status": "live", "home_score": None, "away_score": None, "event_count": 0}],
        row_value=_value,
    )
    assert impact.blocked is True
    assert impact.downstream_match_ids == (20,)


def test_changed_winner_blocked_when_downstream_finished():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="away",
        downstream_rows=[{"id": 21, "match_status": "finished", "home_score": 1, "away_score": 0, "event_count": 0}],
        row_value=_value,
    )
    assert impact.blocked is True


def test_changed_winner_blocked_when_downstream_has_events_even_without_score():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="away",
        downstream_rows=[{"id": 22, "match_status": "not_started", "home_score": None, "away_score": None, "event_count": 2}],
        row_value=_value,
    )
    assert impact.blocked is True


def test_changed_winner_blocked_when_downstream_has_result_despite_not_started_status():
    impact = dependency_impact(
        old_winner_side="home",
        new_winner_side="away",
        downstream_rows=[{"id": 23, "match_status": "not_started", "home_score": 0, "away_score": 0, "event_count": 0}],
        row_value=_value,
    )
    assert impact.blocked is True


def test_winner_side_uses_score_then_penalties():
    assert winner_side(home_score=3, away_score=1) == "home"
    assert winner_side(home_score=1, away_score=2) == "away"
    assert winner_side(home_score=1, away_score=1, home_penalties=5, away_penalties=4) == "home"


def test_central_result_writer_enforces_dependency_guard():
    start = APP.index("def update_match_result_if_unchanged(")
    end = APP.index("def update_player_match_stats_if_unchanged(", start)
    block = APP[start:end]
    assert 'globals().get("_playoff_dependency_guard")' in block
    assert 'if dependency_guard["blocked"]:' in block
    assert "return False" in block


def test_guard_detects_winner_and_loser_dependencies():
    start = APP.index("def _playoff_dependency_guard(")
    end = APP.index("def update_match_result_if_unchanged(", start)
    block = APP[start:end]
    assert "transitive_downstream_match_ids(" in block
    helper = Path("cupnavi_core/playoff_dependency_safety.py").read_text(encoding="utf-8")
    assert 'f"winner:{current_id}"' in helper
    assert 'f"loser:{current_id}"' in helper
    assert "player_match_stats" in block


def test_schedule_bulk_direct_sql_has_same_guard():
    start = APP.index("def _save_bulk_schedule_results")
    end = APP.index('if admin_page == "Skapa och publicera schema":', start)
    block = APP[start:end]
    assert "_playoff_dependency_guard(" in block
    assert "dependency_blocked" in block
