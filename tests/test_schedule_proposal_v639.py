from cupnavi_api.schedule_proposal import build_schedule_proposal


def _match(match_id, home, away, **extra):
    row = {
        "id": match_id,
        "group_id": 1,
        "stage": "group",
        "match_no": match_id,
        "round_no": match_id,
        "home_source": home,
        "away_source": away,
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": False,
        "played": False,
        "home_score": None,
        "away_score": None,
    }
    row.update(extra)
    return row


def _rules(**overrides):
    values = {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 30,
    }
    values.update(overrides)
    return values


def _windows(pitches=1, start="09:00", end="12:00"):
    return [
        {"pitch_number": pitch, "play_date": "2026-09-12", "start_time": start, "end_time": end, "confirmed": True}
        for pitch in range(1, pitches + 1)
    ]


def test_proposal_is_deterministic_and_review_only():
    matches = [
        _match(2, "team:3", "team:4"),
        _match(1, "team:1", "team:2"),
    ]
    forward = build_schedule_proposal(matches, _rules(), _windows(2))
    backward = build_schedule_proposal(list(reversed(matches)), _rules(), _windows(2))
    assert forward == backward
    assert forward["deterministic"] is True
    assert forward["writes_database"] is False
    assert forward["placed_count"] == 2


def test_existing_schedule_is_preserved_and_blocks_pitch():
    fixed = _match(
        1,
        "team:1",
        "team:2",
        scheduled_start="2026-09-12T09:00",
        pitch_number=1,
    )
    result = build_schedule_proposal([fixed, _match(2, "team:3", "team:4")], _rules(), _windows())
    assert result["preserved_count"] == 1
    assert result["placements"][0]["scheduled_start"] == "2026-09-12T09:50"


def test_minimum_team_rest_is_enforced_across_pitches():
    matches = [
        _match(1, "team:1", "team:2"),
        _match(2, "team:1", "team:3"),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows(2))
    first, second = result["placements"]
    assert first["scheduled_start"] == "2026-09-12T09:00"
    assert second["scheduled_start"] >= "2026-09-12T10:15"


def test_locked_unscheduled_match_is_not_moved():
    result = build_schedule_proposal(
        [_match(7, "team:1", "team:2", schedule_locked=True)],
        _rules(),
        _windows(),
    )
    assert result["placed_count"] == 0
    assert result["unresolved"] == [{"match_id": 7, "reason": "locked_without_schedule"}]


def test_capacity_shortage_is_explicit():
    matches = [
        _match(1, "team:1", "team:2"),
        _match(2, "team:3", "team:4"),
        _match(3, "team:5", "team:6"),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows(end="09:00"))
    assert result["placed_count"] == 1
    assert result["unresolved_count"] == 2
    assert {item["reason"] for item in result["unresolved"]} == {"no_feasible_slot"}


def test_unresolved_playoff_participants_do_not_create_fake_team_rest():
    matches = [
        _match(1, "winner:qf1", "team:2"),
        _match(2, "winner:qf1", "team:3"),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows(2))
    assert result["placed_count"] == 2
    assert result["placements"][0]["scheduled_start"] == "2026-09-12T09:00"
    assert result["placements"][1]["scheduled_start"] == "2026-09-12T09:00"
