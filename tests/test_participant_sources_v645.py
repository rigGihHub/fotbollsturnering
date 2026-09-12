from cupnavi_api.schedule_conflicts import analyze_schedule_conflicts
from cupnavi_api.schedule_dependencies import (
    dependency_depths,
    participant_source_dependencies,
    schedule_dependencies,
    structural_playoff_dependencies,
)
from cupnavi_api.schedule_proposal import build_schedule_proposal
from cupnavi_core.participant_sources import parse_participant_source, team_id_from_source


def _rules():
    return {
        "halves": 1,
        "minutes_per_half": 20,
        "halftime_minutes": 0,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 10,
    }


def _row(match_id, *, stage="Slutspel", group_id=None, bracket_id=None, round_no=1, match_no=1,
         home_source=None, away_source=None, scheduled_start=None, pitch_number=None):
    return {
        "id": match_id,
        "stage": stage,
        "group_id": group_id,
        "bracket_id": bracket_id,
        "round_no": round_no,
        "match_no": match_no,
        "home_source": home_source,
        "away_source": away_source,
        "scheduled_start": scheduled_start,
        "pitch_number": pitch_number,
        "schedule_locked": False,
        "home_score": None,
        "away_score": None,
    }


def _windows(end="13:00"):
    return [
        {"pitch_number": pitch, "play_date": "2026-09-12", "start_time": "09:00", "end_time": end, "confirmed": True}
        for pitch in (1, 2, 3)
    ]


def test_canonical_participant_source_parser_covers_existing_contract():
    assert parse_participant_source("team:12").kind == "team"
    assert team_id_from_source("team:12") == 12
    group = parse_participant_source("group:4:2")
    assert (group.kind, group.source_id, group.placement, group.canonical) == ("group", 4, 2, True)
    assert parse_participant_source("winner:19").source_id == 19
    assert parse_participant_source("loser:19").source_id == 19


def test_malformed_canonical_and_legacy_text_are_not_guessed():
    assert parse_participant_source("winner:nope").kind == "invalid"
    assert parse_participant_source("group:2:0").kind == "invalid"
    assert parse_participant_source("Vinnare semifinal A").kind == "legacy"
    assert team_id_from_source("team:nope") is None


def test_explicit_winner_loser_sources_override_structural_guess():
    semi_a = _row(10, bracket_id=7, round_no=1, match_no=1)
    semi_b = _row(11, bracket_id=7, round_no=1, match_no=2)
    bronze = _row(12, bracket_id=7, round_no=2, match_no=1, home_source="loser:10", away_source="loser:11")
    assert structural_playoff_dependencies([semi_a, semi_b, bronze]) == {12: (10, 11)}
    assert participant_source_dependencies([semi_a, semi_b, bronze]) == {12: (10, 11)}
    assert schedule_dependencies([semi_a, semi_b, bronze]) == {12: (10, 11)}

    special = dict(bronze, away_source="team:99")
    assert participant_source_dependencies([semi_a, semi_b, special]) == {12: (10,)}
    assert schedule_dependencies([semi_a, semi_b, special]) == {12: (10,)}


def test_group_source_depends_on_every_group_stage_match():
    group_rows = [
        _row(1, stage="Gruppspel", group_id=4, bracket_id=None, round_no=1, match_no=1, home_source="team:1", away_source="team:2"),
        _row(2, stage="Gruppspel", group_id=4, bracket_id=None, round_no=2, match_no=2, home_source="team:1", away_source="team:3"),
        _row(3, stage="Gruppspel", group_id=4, bracket_id=None, round_no=3, match_no=3, home_source="team:2", away_source="team:3"),
    ]
    quarter = _row(20, bracket_id=8, home_source="group:4:1", away_source="team:9")
    matches = [*group_rows, quarter]
    assert participant_source_dependencies(matches) == {20: (1, 2, 3)}
    assert dependency_depths(matches)[20] == 1


def test_group_qualifier_cannot_start_before_group_finishes_plus_rest():
    matches = [
        _row(1, stage="Gruppspel", group_id=4, round_no=1, match_no=1, home_source="team:1", away_source="team:2", scheduled_start="2026-09-12T09:00", pitch_number=1),
        _row(2, stage="Gruppspel", group_id=4, round_no=2, match_no=2, home_source="team:1", away_source="team:3", scheduled_start="2026-09-12T10:00", pitch_number=1),
        _row(20, bracket_id=8, home_source="group:4:1", away_source="team:9", scheduled_start="2026-09-12T10:20", pitch_number=2),
    ]
    analysis = analyze_schedule_conflicts(matches, _rules())
    conflicts = [item for item in analysis["conflicts"] if item["type"] == "playoff_dependency"]
    assert len(conflicts) == 1
    assert conflicts[0]["downstream_match_id"] == 20
    assert conflicts[0]["upstream_match_ids"] == [1, 2]
    assert conflicts[0]["earliest_start"] == "2026-09-12T10:30"


def test_proposal_schedules_group_before_group_qualified_playoff_match():
    matches = [
        _row(1, stage="Gruppspel", group_id=4, round_no=1, match_no=1, home_source="team:1", away_source="team:2"),
        _row(2, stage="Gruppspel", group_id=4, round_no=2, match_no=2, home_source="team:1", away_source="team:3"),
        _row(20, bracket_id=8, round_no=1, match_no=1, home_source="group:4:1", away_source="team:9"),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows())
    placements = {item["match_id"]: item for item in result["placements"]}
    assert set(placements) == {1, 2, 20}
    assert placements[20]["scheduled_start"] >= "2026-09-12T10:10"
    assert result["quality"]["participant_source_dependency_enforced"] is True


def test_legacy_text_keeps_v644_structural_fallback():
    semi_a = _row(10, bracket_id=7, round_no=1, match_no=1, home_source="A", away_source="B")
    semi_b = _row(11, bracket_id=7, round_no=1, match_no=2, home_source="C", away_source="D")
    final = _row(12, bracket_id=7, round_no=2, match_no=1, home_source="Vinnare semifinal A", away_source="Vinnare semifinal B")
    assert schedule_dependencies([semi_a, semi_b, final]) == {12: (10, 11)}
