from pathlib import Path

from cupnavi_core.match_engine import aggregate_result, match_format, score_model, validate_segment_scores
from cupnavi_core.schedule_optimizer import optimize_match_order


def test_team_and_set_sports_have_distinct_match_models():
    football = match_format("football")
    hockey = match_format("ice_hockey")
    tennis = match_format("tennis")
    volleyball = match_format("volleyball")
    assert football.segment_kind == "half"
    assert football.scoring_mode == "aggregate"
    assert football.supports_draw is True
    assert hockey.segment_kind == "period"
    assert hockey.discipline_mode == "penalty_minutes"
    assert tennis.segment_kind == "set"
    assert tennis.scoring_mode == "set_based"
    assert tennis.participant_type == "individual_or_pair"
    assert volleyball.win_condition == "sets_won"


def test_set_based_scores_aggregate_to_sets_won():
    result = aggregate_result("tennis", [
        {"home": 6, "away": 4},
        {"home": 3, "away": 6},
        {"home": 7, "away": 5},
    ])
    assert result == {"ok": True, "home": 2, "away": 1, "mode": "set_based"}


def test_set_based_segment_must_have_winner():
    result = validate_segment_scores("padel", [{"home": 6, "away": 6}])
    assert result["ok"] is False
    assert "vinnare" in result["errors"][0]


def test_score_model_is_language_independent():
    model = score_model("Fotboll")
    assert model["sport_id"] == "football"
    assert model["scoring_mode"] == "aggregate"


def test_schedule_optimizer_returns_every_match_once_without_ortools_requirement():
    matches = [
        ({"id": 1}, 1, 2),
        ({"id": 2}, 1, 3),
        ({"id": 3}, 4, 5),
        ({"id": 4}, 2, 3),
    ]
    order, engine = optimize_match_order(matches, pitch_count=2)
    assert sorted(order) == list(range(len(matches)))
    assert engine in {"ortools-cp-sat", "greedy-fallback", "trivial"}


def test_release_declares_ortools_and_uses_optimizer():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    app = Path("app.py").read_text(encoding="utf-8")
    assert "ortools>=9.10,<10" in requirements
    assert "optimize_match_order(" in app
    assert "match_format(saved_sport)" in app
