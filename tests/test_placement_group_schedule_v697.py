from cupnavi_api.schedule_dependencies import dependency_depths, participant_source_dependencies
from cupnavi_api.schedule_proposal import build_schedule_proposal


def _row(match_id, *, stage="Gruppspel", group_id=None, home_source=None, away_source=None):
    return {
        "id": match_id,
        "stage": stage,
        "group_id": group_id,
        "bracket_id": None,
        "round_no": 1,
        "match_no": match_id,
        "home_source": home_source,
        "away_source": away_source,
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": False,
        "home_score": None,
        "away_score": None,
    }


def _rules():
    return {
        "halves": 1,
        "minutes_per_half": 20,
        "halftime_minutes": 0,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 10,
    }


def _windows():
    return [
        {"pitch_number": pitch, "play_date": "2026-09-12", "start_time": "09:00", "end_time": "15:00", "confirmed": True}
        for pitch in (1, 2, 3)
    ]


def test_placement_group_match_waits_for_all_referenced_preliminary_groups():
    matches = [
        _row(1, group_id=10, home_source="team:1", away_source="team:2"),
        _row(2, group_id=10, home_source="team:1", away_source="team:3"),
        _row(3, group_id=20, home_source="team:4", away_source="team:5"),
        _row(4, group_id=20, home_source="team:4", away_source="team:6"),
        _row(10, stage="Placeringsgrupp", home_source="group:10:1", away_source="group:20:1"),
    ]
    assert participant_source_dependencies(matches)[10] == (1, 2, 3, 4)
    assert dependency_depths(matches)[10] == 1


def test_schedule_proposal_places_placement_group_after_preliminary_matches():
    matches = [
        _row(1, group_id=10, home_source="team:1", away_source="team:2"),
        _row(2, group_id=20, home_source="team:3", away_source="team:4"),
        _row(10, stage="Placeringsgrupp", home_source="group:10:1", away_source="group:20:1"),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows())
    placements = {item["match_id"]: item for item in result["placements"]}
    assert set(placements) == {1, 2, 10}
    assert placements[10]["scheduled_start"] >= "2026-09-12T09:30"
    assert result["quality"]["participant_source_dependency_enforced"] is True
