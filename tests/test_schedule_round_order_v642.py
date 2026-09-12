from cupnavi_api.schedule_proposal import build_schedule_proposal


def _match(match_id, round_no, **extra):
    row = {
        "id": match_id,
        "group_id": 1,
        "stage": "group",
        "match_no": match_id,
        "round_no": round_no,
        "home_source": f"team:{match_id * 2 - 1}",
        "away_source": f"team:{match_id * 2}",
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": False,
        "played": False,
        "home_score": None,
        "away_score": None,
    }
    row.update(extra)
    return row


def _rules():
    return {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 0,
    }


def _windows(start="09:00", end="11:30"):
    return [
        {"pitch_number": pitch, "play_date": "2026-09-12", "start_time": start, "end_time": end, "confirmed": True}
        for pitch in (1, 2)
    ]


def test_lower_round_is_placed_before_fixed_higher_round_when_possible():
    fixed_round_two = _match(2, 2, scheduled_start="2026-09-12T09:50", pitch_number=2)
    round_one = _match(1, 1)
    result = build_schedule_proposal([fixed_round_two, round_one], _rules(), _windows())
    assert result["placements"] == [{"match_id": 1, "scheduled_start": "2026-09-12T09:00", "pitch_number": 1}]
    assert result["quality"]["round_order_violation_count"] == 0


def test_round_order_blocks_new_inversion_against_fixed_match():
    fixed_round_two = _match(2, 2, scheduled_start="2026-09-12T09:00", pitch_number=2)
    round_one = _match(1, 1)
    result = build_schedule_proposal([fixed_round_two, round_one], _rules(), _windows(start="09:00", end="11:30"))
    assert result["placed_count"] == 0
    assert result["unresolved"] == [{"match_id": 1, "reason": "round_order_blocked"}]
    assert result["quality"]["round_order_enforced"] is True


def test_round_two_cannot_kick_off_before_round_one_in_same_group():
    round_two = _match(2, 2)
    round_one = _match(1, 1)
    result = build_schedule_proposal([round_two, round_one], _rules(), _windows())
    placements = {item["match_id"]: item for item in result["placements"]}
    assert placements[1]["scheduled_start"] <= placements[2]["scheduled_start"]
    assert result["quality"]["round_order_violation_count"] == 0


def test_round_order_is_scoped_per_group():
    fixed_group_one_round_two = _match(2, 2, scheduled_start="2026-09-12T09:00", pitch_number=2)
    other_group_round_one = _match(3, 1, group_id=2)
    result = build_schedule_proposal([fixed_group_one_round_two, other_group_round_one], _rules(), _windows())
    assert result["placed_count"] == 1
    assert result["placements"][0]["scheduled_start"] == "2026-09-12T09:00"
    assert result["placements"][0]["pitch_number"] == 1


def test_quality_exposes_schedule_span():
    matches = [_match(1, 1), _match(2, 2)]
    result = build_schedule_proposal(matches, _rules(), _windows())
    assert result["quality"]["schedule_span_minutes"] >= 0
    assert result["quality"]["strategy"] == "bounded_pitch_continuity_and_rest"
