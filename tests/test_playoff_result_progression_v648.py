import pytest

from cupnavi_core.playoff_result_progression import (
    decided_side_from_team_id,
    prepare_result,
)


def test_group_result_never_carries_penalty_or_winner_state():
    result = prepare_result(
        stage="Gruppspel",
        home_score=2,
        away_score=2,
        home_penalties=5,
        away_penalties=4,
        home_team_id=1,
        away_team_id=2,
    )
    assert result.outcome_resolved is True
    assert result.home_penalties is None
    assert result.away_penalties is None
    assert result.winner_side is None
    assert result.decided_winner_id is None


def test_regular_knockout_win_is_decisive_without_penalties():
    result = prepare_result(
        stage="Semifinal",
        home_score=3,
        away_score=1,
        home_team_id=11,
        away_team_id=12,
    )
    assert result.outcome_resolved is True
    assert result.winner_side == "home"
    assert result.decided_winner_id == 11
    assert result.home_penalties is None
    assert result.away_penalties is None


def test_tied_knockout_score_can_be_saved_as_awaiting_decision():
    result = prepare_result(
        stage="Final",
        home_score=1,
        away_score=1,
        home_team_id=11,
        away_team_id=12,
    )
    assert result.outcome_resolved is False
    assert result.winner_side is None


def test_incomplete_or_equal_penalty_result_is_rejected():
    with pytest.raises(ValueError, match="både hemma- och bortastraffar"):
        prepare_result(stage="Final", home_score=1, away_score=1, home_penalties=4)
    with pytest.raises(ValueError, match="måste avgöra"):
        prepare_result(stage="Final", home_score=1, away_score=1, home_penalties=4, away_penalties=4)


def test_penalty_result_resolves_actual_team():
    result = prepare_result(
        stage="Final",
        home_score=2,
        away_score=2,
        home_penalties=3,
        away_penalties=5,
        home_team_id=11,
        away_team_id=12,
    )
    assert result.outcome_resolved is True
    assert result.winner_side == "away"
    assert result.decided_winner_id == 12


def test_negative_scores_are_rejected():
    with pytest.raises(ValueError, match="kan inte vara negativt"):
        prepare_result(stage="Gruppspel", home_score=-1, away_score=0)


def test_persisted_manual_winner_maps_only_to_current_participants():
    assert decided_side_from_team_id(11, home_team_id=11, away_team_id=12) == "home"
    assert decided_side_from_team_id(12, home_team_id=11, away_team_id=12) == "away"
    assert decided_side_from_team_id(99, home_team_id=11, away_team_id=12) is None
