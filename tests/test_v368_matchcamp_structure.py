from pathlib import Path

from cupnavi_core.matchcamp_structure import (
    build_matchcamp_structure_improvement,
    matchcamp_structure_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")


def _teams():
    return [
        {"id": 1, "group_id": 10, "name": "A"},
        {"id": 2, "group_id": 10, "name": "B"},
        {"id": 3, "group_id": 10, "name": "C"},
        {"id": 4, "group_id": 10, "name": "D"},
    ]


def _match(mid, home, away, *, locked=0, home_score=None, away_score=None):
    return {
        "id": mid,
        "group_id": 10,
        "stage": "Gruppspel",
        "scheduled_start": None,
        "pitch_number": None,
        "referee_id": None,
        "home_source": f"team:{home}",
        "away_source": f"team:{away}",
        "home_score": home_score,
        "away_score": away_score,
        "schedule_locked": locked,
    }


def test_structure_optimizer_can_balance_match_counts_and_remove_repeat():
    matches = [
        _match(1, 1, 2),
        _match(2, 1, 2),
        _match(3, 1, 3),
        _match(4, 1, 4),
    ]
    before = matchcamp_structure_metrics(matches, _teams(), match_duration_minutes=25)
    proposal = build_matchcamp_structure_improvement(
        matches,
        _teams(),
        match_duration_minutes=25,
        minimum_rest_minutes=25,
    )
    assert before["match_count_spread"] == 3
    assert before["repeated_opponents"] == 1
    assert proposal["improved"] is True
    assert proposal["after"]["objective"] < proposal["before"]["objective"]
    assert proposal["after"]["match_count_spread"] < before["match_count_spread"]
    assert proposal["after"]["repeated_opponents"] <= before["repeated_opponents"]
    assert proposal["updates"]


def test_structure_optimizer_never_changes_locked_or_played_rows():
    matches = [
        _match(1, 1, 2, locked=1),
        _match(2, 1, 2, home_score=1, away_score=0),
        _match(3, 1, 3),
        _match(4, 1, 4),
    ]
    proposal = build_matchcamp_structure_improvement(
        matches,
        _teams(),
        match_duration_minutes=25,
        minimum_rest_minutes=25,
    )
    changed_ids = {row["id"] for row in proposal["updates"]}
    assert 1 not in changed_ids
    assert 2 not in changed_ids


def test_protected_team_is_never_removed_or_added_by_changed_row():
    matches = [
        _match(1, 1, 2),
        _match(2, 1, 2),
        _match(3, 1, 3),
        _match(4, 1, 4),
    ]
    proposal = build_matchcamp_structure_improvement(
        matches,
        _teams(),
        match_duration_minutes=25,
        minimum_rest_minutes=25,
        protected_team_ids={1},
    )
    for update in proposal["updates"]:
        sources = {
            update["expected_home_source"],
            update["expected_away_source"],
            update["home_source"],
            update["away_source"],
        }
        assert "team:1" not in sources


def test_workspace_is_preview_first_and_matchcamp_only():
    assert "#### Förbättra matchfördelningen" in WORKSPACE
    assert "Beräkna bättre matchfördelning" in WORKSPACE
    assert "Använd den bättre matchfördelningen" in WORKSPACE
    assert "if _show_optimizer and _optimizer_is_matchcamp:" in WORKSPACE
    assert "build_matchcamp_structure_improvement" in WORKSPACE


def test_persistence_uses_optimistic_source_checks_and_forces_recheck():
    assert "def _apply_matchcamp_structure_improvement" in APP
    assert "AND home_source=? AND away_source=?" in APP
    assert "home_score IS NULL AND away_score IS NULL" in APP
    assert "schedule_locked=0" in APP
    assert "SET is_published=0,schedule_dirty=1" in APP
