from pathlib import Path

from cupnavi_core.match_event_logic import (
    prepare_live_goal_change,
    validate_result_against_linked_goals,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"


def test_release_version():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert VERSION in APP


def test_result_cannot_be_lower_than_linked_home_goals():
    verdict = validate_result_against_linked_goals(
        home_score=2, away_score=1, home_linked_goals=3, away_linked_goals=1
    )
    assert verdict["ok"] is False
    assert "hemmalaget har 3" in verdict["message"]


def test_result_cannot_be_lower_than_linked_away_goals():
    verdict = validate_result_against_linked_goals(
        home_score=2, away_score=1, home_linked_goals=2, away_linked_goals=2
    )
    assert verdict["ok"] is False
    assert "bortalaget har 2" in verdict["message"]


def test_team_score_may_exceed_linked_goals_for_unknown_or_own_goal():
    verdict = validate_result_against_linked_goals(
        home_score=3, away_score=1, home_linked_goals=2, away_linked_goals=1
    )
    assert verdict["ok"] is True


def test_result_cannot_be_cleared_while_player_goals_exist():
    verdict = validate_result_against_linked_goals(
        home_score=None, away_score=None, home_linked_goals=1, away_linked_goals=0
    )
    assert verdict["ok"] is False
    assert "målskyttar" in verdict["message"]


def test_rehearsal_sequence_goal_undo_and_final_result_integrity():
    home = away = None
    linked_home = linked_away = 0

    goal = prepare_live_goal_change(
        home_score=home, away_score=away,
        home_team_id=10, away_team_id=20, team_id=10, delta=1,
    )
    home, away = goal["home_score"], goal["away_score"]
    linked_home += 1
    assert (home, away, linked_home, linked_away) == (1, 0, 1, 0)
    assert validate_result_against_linked_goals(
        home_score=home, away_score=away,
        home_linked_goals=linked_home, away_linked_goals=linked_away,
    )["ok"]

    goal = prepare_live_goal_change(
        home_score=home, away_score=away,
        home_team_id=10, away_team_id=20, team_id=20, delta=1,
    )
    home, away = goal["home_score"], goal["away_score"]
    linked_away += 1
    assert (home, away) == (1, 1)

    undo = prepare_live_goal_change(
        home_score=home, away_score=away,
        home_team_id=10, away_team_id=20, team_id=20, delta=-1,
    )
    home, away = undo["home_score"], undo["away_score"]
    linked_away -= 1
    assert (home, away, linked_home, linked_away) == (1, 0, 1, 0)

    bad_final = validate_result_against_linked_goals(
        home_score=0, away_score=0,
        home_linked_goals=linked_home, away_linked_goals=linked_away,
    )
    good_final = validate_result_against_linked_goals(
        home_score=1, away_score=0,
        home_linked_goals=linked_home, away_linked_goals=linked_away,
    )
    assert bad_final["ok"] is False
    assert good_final["ok"] is True


def test_quick_bulk_and_admin_result_paths_all_guard_event_integrity():
    quick = APP[APP.index("def _reporter_save_quick_result"):APP.index("def _reporter_save_bulk_results")]
    bulk = APP[APP.index("def _reporter_save_bulk_results"):APP.index("def _reporter_live_goal_transaction")]
    admin_start = APP.index("def _save_admin_result_updates")
    admin = APP[admin_start:APP.index("render_admin_results_workspace", admin_start)]
    assert "_result_event_integrity(" in quick
    assert "_result_event_integrity(" in bulk
    assert "_result_event_integrity(" in admin
    assert "integrity_blocked_updates" in admin


def test_specific_integrity_warning_survives_quick_result_callback():
    callback = VIEW[VIEW.index("def _save_quick_result_callback"):VIEW.index("def _set_match_status_callback")]
    assert 'if "reporter_result_warning" not in st.session_state:' in callback
