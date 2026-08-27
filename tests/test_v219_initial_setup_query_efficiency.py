
from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


def _setup():
    return APP[
        APP.index("def render_initial_tournament_setup"):
        APP.index("def _render_with_friendly_error")
    ]


def test_played_match_count_is_reused_for_class_lock():
    setup=_setup()
    assert "_class_played_count=_played_setup" in setup
    assert setup.count(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL"
    ) == 1


def test_competition_classes_are_loaded_once_per_setup_rerun():
    setup=_setup()
    assert setup.count("competition_classes(tournament_id)") == 1
    assert "_planned_by_class=_planned_total" in setup


def test_pitch_windows_are_reused_for_capacity_and_recommendation():
    setup=_setup()
    assert "_capacity_windows=pitch_day_windows(" not in setup
    assert "_rec_windows=pitch_day_windows(" not in setup
    assert "_capacity_windows=windows" in setup
    assert "_rec_windows=windows" in setup


def test_team_counts_are_batched_not_queried_per_class():
    setup=_setup()
    assert "GROUP BY competition_class_id" in setup
    assert "_team_count_by_class" in setup
    assert 'SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND competition_class_id=?' not in setup
    assert 'SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?",(tournament_id,)' not in setup
