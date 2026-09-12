from datetime import datetime

from cupnavi_core.schedule_generation import build_schedule_preview


def _tournament():
    return {"start_date": "2026-09-20", "end_date": "2026-09-20", "playoff_tie_rule": "Straffar direkt"}


def _rules(**overrides):
    values = {
        "first_match_time": "09:00",
        "latest_kickoff_time": "18:00",
        "pitch_count": 1,
        "halves": 2,
        "minutes_per_half": 10,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 30,
    }
    values.update(overrides)
    return values


def _match(mid, home, away, **extra):
    row = {
        "id": mid,
        "stage": "Gruppspel",
        "home_source": f"team:{home}",
        "away_source": f"team:{away}",
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": 0,
        "home_score": None,
        "away_score": None,
        "referee_id": None,
    }
    row.update(extra)
    return row


def test_preview_preserves_played_locked_and_already_scheduled_matches():
    matches = [
        _match(1, 1, 2, scheduled_start="2026-09-20T09:00", pitch_number=1),
        _match(2, 3, 4, home_score=1, away_score=0),
        _match(3, 5, 6, schedule_locked=1),
        _match(4, 7, 8),
    ]
    preview = build_schedule_preview(matches, _tournament(), _rules())
    assert preview["preserved_count"] == 3
    assert [row["id"] for row in preview["updates"]] == [4]


def test_preview_respects_minimum_rest_for_same_team():
    matches = [_match(1, 1, 2), _match(2, 1, 3)]
    preview = build_schedule_preview(matches, _tournament(), _rules(minimum_team_rest_minutes=30))
    assert preview["unresolved_count"] == 0
    starts = {row["id"]: datetime.fromisoformat(row["scheduled_start"]) for row in preview["updates"]}
    # 25 minute match + 30 minute rest = 55 minutes before team 1 may start again.
    assert abs((starts[2] - starts[1]).total_seconds()) >= 55 * 60


def test_preview_marks_symbolic_playoff_dependency_unresolved_instead_of_guessing():
    match = _match(1, 1, 2)
    match["stage"] = "Semifinal"
    match["home_source"] = "rank:group:1:1"
    preview = build_schedule_preview([match], _tournament(), _rules())
    assert preview["updates"] == []
    assert preview["unresolved_match_ids"] == [1]
    assert preview["safe_to_apply"] is False


def test_preview_refuses_capacity_past_last_cup_day():
    matches = [_match(i, i * 2, i * 2 + 1) for i in range(1, 6)]
    preview = build_schedule_preview(matches, _tournament(), _rules(first_match_time="17:30", latest_kickoff_time="18:00"))
    assert preview["unresolved_count"] > 0
    assert preview["safe_to_apply"] is False
