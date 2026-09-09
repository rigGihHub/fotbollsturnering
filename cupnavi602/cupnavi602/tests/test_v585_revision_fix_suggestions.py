from cupnavi_core.revision_import import suggest_match_revision_resolutions


def _m(mid, start, pitch, home, away):
    return {"id": mid, "scheduled_start": start, "pitch_number": pitch, "home": home, "away": away, "phase": "group", "match_status": "not_started"}


def test_suggests_other_pitch_for_collision():
    matches = [
        _m(1, "2026-09-20T10:00", 1, "A", "B"),
        _m(2, "2026-09-20T11:00", 2, "C", "D"),
        _m(3, "2026-09-20T10:00", 2, "E", "F"),
    ]
    selected = [{
        "current": matches[1], "match": "C – D", "played": False,
        "apply_start": "2026-09-20T10:00", "apply_pitch": 1,
    }]
    fixes = suggest_match_revision_resolutions(
        selected, matches, group_duration_minutes=30, playoff_duration_minutes=30,
        pitch_windows=[
            {"pitch_number": 1, "play_date":"2026-09-20", "start_time":"09:00", "end_time":"18:00", "confirmed": True},
            {"pitch_number": 2, "play_date":"2026-09-20", "start_time":"09:00", "end_time":"18:00", "confirmed": True},
        ]
    )
    assert fixes
    assert fixes[0]["match_id"] == 2
    assert fixes[0]["apply_pitch"] == 1
    assert fixes[0]["apply_start"].endswith("10:30")


def test_no_suggestion_for_already_safe_revision():
    matches = [_m(1, "2026-09-20T10:00", 1, "A", "B")]
    selected = [{"current": matches[0], "match":"A – B", "played":False, "apply_start":"2026-09-20T11:00", "apply_pitch":1}]
    fixes = suggest_match_revision_resolutions(selected, matches, group_duration_minutes=30, playoff_duration_minutes=30)
    assert fixes == []
