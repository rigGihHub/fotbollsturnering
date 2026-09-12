from cupnavi_api.schedule_conflicts import analyze_schedule_conflicts


def _match(match_id, start, pitch, home, away):
    return {
        "id": match_id,
        "match_no": match_id,
        "stage": "group",
        "scheduled_start": start,
        "pitch_number": pitch,
        "home_source": home,
        "away_source": away,
        "home_label": home,
        "away_label": away,
    }


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


def test_detects_pitch_overlap_including_configured_pitch_break():
    matches = [
        _match(1, "2026-09-12T09:00", 1, "team:1", "team:2"),
        _match(2, "2026-09-12T09:48", 1, "team:3", "team:4"),
    ]

    result = analyze_schedule_conflicts(matches, _rules())

    pitch = [item for item in result["conflicts"] if item["type"] == "pitch_overlap"]
    assert len(pitch) == 1
    assert pitch[0]["match_ids"] == [1, 2]
    assert pitch[0]["overlap_minutes"] == 2
    assert result["error_count"] == 1


def test_detects_team_overlap_across_different_pitches():
    matches = [
        _match(1, "2026-09-12T09:00", 1, "team:1", "team:2"),
        _match(2, "2026-09-12T09:30", 2, "team:1", "team:3"),
    ]

    result = analyze_schedule_conflicts(matches, _rules(pitch_break_minutes=0))

    team = [item for item in result["conflicts"] if item["type"] == "team_overlap"]
    assert len(team) == 1
    assert team[0]["team_id"] == 1
    assert team[0]["rest_minutes"] == -15
    assert team[0]["severity"] == "error"


def test_detects_insufficient_rest_without_calling_it_overlap():
    matches = [
        _match(1, "2026-09-12T09:00", 1, "team:1", "team:2"),
        _match(2, "2026-09-12T10:00", 2, "team:1", "team:3"),
    ]

    result = analyze_schedule_conflicts(matches, _rules(pitch_break_minutes=0))

    rest = [item for item in result["conflicts"] if item["type"] == "insufficient_rest"]
    assert len(rest) == 1
    assert rest[0]["rest_minutes"] == 15
    assert rest[0]["required_rest_minutes"] == 30
    assert rest[0]["severity"] == "warning"
    assert result["warning_count"] == 1


def test_accepts_exact_minimum_rest_and_pitch_turnaround():
    matches = [
        _match(1, "2026-09-12T09:00", 1, "team:1", "team:2"),
        _match(2, "2026-09-12T09:50", 1, "team:3", "team:4"),
        _match(3, "2026-09-12T10:15", 2, "team:1", "team:5"),
    ]

    result = analyze_schedule_conflicts(matches, _rules())

    assert result["ok"] is True
    assert result["conflict_count"] == 0


def test_ignores_unresolved_playoff_sources_for_team_rest():
    matches = [
        _match(1, "2026-09-12T09:00", 1, "winner:qf1", "team:2"),
        _match(2, "2026-09-12T09:30", 2, "winner:qf1", "team:3"),
    ]

    result = analyze_schedule_conflicts(matches, _rules(pitch_break_minutes=0))

    assert not [
        item for item in result["conflicts"]
        if item["type"] in {"team_overlap", "insufficient_rest"}
    ]


def test_conflict_order_is_deterministic_for_unsorted_input():
    matches = [
        _match(3, "2026-09-12T10:00", 2, "team:1", "team:4"),
        _match(2, "2026-09-12T09:20", 1, "team:3", "team:4"),
        _match(1, "2026-09-12T09:00", 1, "team:1", "team:2"),
    ]

    forward = analyze_schedule_conflicts(matches, _rules())
    backward = analyze_schedule_conflicts(list(reversed(matches)), _rules())

    assert forward == backward


def test_reports_invalid_nonempty_start_without_crashing():
    matches = [_match(7, "not-a-date", 1, "team:1", "team:2")]

    result = analyze_schedule_conflicts(matches, _rules())

    assert result["conflict_count"] == 1
    assert result["conflicts"][0]["type"] == "invalid_start"
    assert result["conflicts"][0]["match_ids"] == [7]
