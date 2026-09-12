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


def _rules():
    return {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 0,
    }


def _windows():
    return [
        {"pitch_number": pitch, "play_date": "2026-09-12", "start_time": "09:00", "end_time": "11:30", "confirmed": True}
        for pitch in (1, 2)
    ]


def test_quality_prefers_same_pitch_when_kickoff_is_equal():
    fixed = _match(1, "team:1", "team:2", scheduled_start="2026-09-12T09:00", pitch_number=2)
    next_match = _match(2, "team:1", "team:3")
    result = build_schedule_proposal([fixed, next_match], _rules(), _windows())
    placement = result["placements"][0]
    assert placement["scheduled_start"] == "2026-09-12T09:50"
    assert placement["pitch_number"] == 2
    assert result["quality"]["plan_change_count"] == 0


def test_quality_never_delays_multiple_slots_just_to_keep_pitch():
    fixed = _match(1, "team:1", "team:2", scheduled_start="2026-09-12T09:00", pitch_number=2)
    blocker = _match(9, "team:9", "team:10", scheduled_start="2026-09-12T09:50", pitch_number=2)
    next_match = _match(2, "team:1", "team:3")
    result = build_schedule_proposal([fixed, blocker, next_match], _rules(), _windows())
    placement = result["placements"][0]
    assert placement["scheduled_start"] == "2026-09-12T09:50"
    assert placement["pitch_number"] == 1
    assert result["quality"]["plan_change_count"] == 1


def test_quality_metrics_are_deterministic():
    matches = [_match(2, "team:3", "team:4"), _match(1, "team:1", "team:2")]
    forward = build_schedule_proposal(matches, _rules(), _windows())
    backward = build_schedule_proposal(list(reversed(matches)), _rules(), _windows())
    assert forward == backward
    assert forward["quality"]["strategy"] == "bounded_pitch_continuity_and_rest"
