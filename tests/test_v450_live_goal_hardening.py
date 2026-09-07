from pathlib import Path

import pytest

from cupnavi_core.match_event_logic import prepare_live_goal_change

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"


def test_release_version():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert VERSION in APP


def test_first_live_goal_starts_from_zero_zero():
    change = prepare_live_goal_change(
        home_score=None, away_score=None, home_team_id=10, away_team_id=20, team_id=10
    )
    assert (change["home_score"], change["away_score"]) == (1, 0)


def test_away_live_goal_increments_only_away_score():
    change = prepare_live_goal_change(
        home_score=2, away_score=1, home_team_id=10, away_team_id=20, team_id=20
    )
    assert (change["home_score"], change["away_score"]) == (2, 2)


def test_undo_cannot_make_score_negative():
    with pytest.raises(ValueError):
        prepare_live_goal_change(
            home_score=0, away_score=0, home_team_id=10, away_team_id=20, team_id=10, delta=-1
        )


def test_non_participant_team_is_rejected():
    with pytest.raises(ValueError):
        prepare_live_goal_change(
            home_score=0, away_score=0, home_team_id=10, away_team_id=20, team_id=30
        )


def test_live_goal_is_atomic_and_optimistically_locked():
    block = APP[APP.index("def _reporter_live_goal_transaction"):APP.index("def _reporter_save_event_rows")]
    assert 'con.execute("BEGIN" if CLOUD_DATABASE_ENABLED else "BEGIN IMMEDIATE")' in block
    assert "update_match_result_if_unchanged(" in block
    assert "update_player_match_stats_if_unchanged(" in block
    assert "con.rollback()" in block
    assert "con.commit()" in block
    assert "enqueue_goal_push_events(con, **goal_push)" in block


def test_live_goal_checks_match_and_player_ownership():
    block = APP[APP.index("def _reporter_live_goal_transaction"):APP.index("def _reporter_save_event_rows")]
    assert "t.tournament_id=?" in block
    assert "p.team_id=?" in block
    assert "Matchen finns inte längre i den här cupen." in block
    assert "Spelaren tillhör inte det valda laget." in block


def test_live_goal_ui_updates_score_and_scorer_together():
    assert '"⚽ MÅL · uppdatera resultat"' in VIEW
    assert "deps.save_live_goal(" in VIEW
    assert "Ett tryck sparar både matchresultat och målskytt i samma transaktion." in VIEW


def test_atomic_undo_is_available_for_last_live_goal():
    assert 'bool(detail.get("atomic_goal"))' in VIEW
    assert "deps.undo_live_goal(" in VIEW
    assert "Målet och matchresultatet ångrades tillsammans." in VIEW


def test_finished_match_uses_scorer_completion_not_score_increment():
    assert 'if match_status != MATCH_FINISHED:' in VIEW
    assert 'action_specs = [("goals", "⚽ + Målskytt", "Mål")]' in VIEW
