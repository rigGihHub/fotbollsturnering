from cupnavi_api.schedule_conflicts import analyze_schedule_conflicts
from cupnavi_api.schedule_dependencies import structural_playoff_dependencies
from cupnavi_api.schedule_proposal import build_schedule_proposal, schedule_proposal_fingerprint
from cupnavi_core.admin_publication import build_publish_blockers


def _rules():
    return {
        "halves": 1,
        "minutes_per_half": 20,
        "halftime_minutes": 0,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 10,
    }


def _match(match_id, round_no, match_no, **extra):
    row = {
        "id": match_id,
        "group_id": None,
        "bracket_id": 7,
        "stage": "Slutspel",
        "round_no": round_no,
        "match_no": match_no,
        "home_source": f"legacy-home-{match_id}",
        "away_source": f"legacy-away-{match_id}",
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": False,
        "home_score": None,
        "away_score": None,
    }
    row.update(extra)
    return row


def _windows(end="12:00"):
    return [
        {
            "pitch_number": pitch,
            "play_date": "2026-09-12",
            "start_time": "09:00",
            "end_time": end,
            "confirmed": True,
        }
        for pitch in (1, 2, 3)
    ]


def test_structural_dependency_maps_two_semifinals_to_final():
    matches = [_match(1, 1, 1), _match(2, 1, 2), _match(3, 2, 1)]
    assert structural_playoff_dependencies(matches) == {3: (1, 2)}


def test_conflict_detects_final_before_later_semifinal_plus_rest():
    matches = [
        _match(1, 1, 1, scheduled_start="2026-09-12T09:00", pitch_number=1),
        _match(2, 1, 2, scheduled_start="2026-09-12T09:50", pitch_number=2),
        _match(3, 2, 1, scheduled_start="2026-09-12T10:00", pitch_number=3),
    ]
    analysis = analyze_schedule_conflicts(matches, _rules())
    dependency = [item for item in analysis["conflicts"] if item["type"] == "playoff_dependency"]
    assert len(dependency) == 1
    assert dependency[0]["downstream_match_id"] == 3
    assert dependency[0]["upstream_match_ids"] == [1, 2]
    assert dependency[0]["earliest_start"] == "2026-09-12T10:20"
    assert dependency[0]["shortage_minutes"] == 20
    assert dependency[0]["severity"] == "error"


def test_exact_dependency_threshold_is_allowed():
    matches = [
        _match(1, 1, 1, scheduled_start="2026-09-12T09:00", pitch_number=1),
        _match(2, 1, 2, scheduled_start="2026-09-12T09:50", pitch_number=2),
        _match(3, 2, 1, scheduled_start="2026-09-12T10:20", pitch_number=3),
    ]
    analysis = analyze_schedule_conflicts(matches, _rules())
    assert not [item for item in analysis["conflicts"] if item["type"] == "playoff_dependency"]


def test_scheduled_final_with_unscheduled_semifinal_is_blocking():
    matches = [
        _match(1, 1, 1, scheduled_start="2026-09-12T09:00", pitch_number=1),
        _match(2, 1, 2),
        _match(3, 2, 1, scheduled_start="2026-09-12T10:20", pitch_number=3),
    ]
    analysis = analyze_schedule_conflicts(matches, _rules())
    errors = [item for item in analysis["conflicts"] if item["type"] == "playoff_dependency"]
    assert len(errors) == 1
    blockers = build_publish_blockers(
        playoff_model_confirmed=True,
        scheduled_matches=2,
        schedule_dirty=False,
        schedule_errors=[item["message"] for item in errors],
    )
    assert blockers == ["1 blockerande schemafel måste åtgärdas."]


def test_proposal_places_final_only_after_structural_dependencies():
    matches = [_match(1, 1, 1), _match(2, 1, 2), _match(3, 2, 1)]
    result = build_schedule_proposal(matches, _rules(), _windows())
    placements = {item["match_id"]: item for item in result["placements"]}
    assert set(placements) == {1, 2, 3}
    assert placements[1]["scheduled_start"] == "2026-09-12T09:00"
    assert placements[2]["scheduled_start"] == "2026-09-12T09:00"
    assert placements[3]["scheduled_start"] >= "2026-09-12T09:40"
    assert result["quality"]["playoff_dependency_enforced"] is True


def test_unresolved_upstream_blocks_downstream_proposal():
    matches = [
        _match(1, 1, 1, schedule_locked=True),
        _match(2, 1, 2),
        _match(3, 2, 1),
    ]
    result = build_schedule_proposal(matches, _rules(), _windows())
    unresolved = {item["match_id"]: item["reason"] for item in result["unresolved"]}
    assert unresolved[1] == "locked_without_schedule"
    assert unresolved[3] == "playoff_dependency_blocked"


def test_legacy_placeholder_text_does_not_create_guessed_dependency():
    final_only = _match(
        3,
        2,
        1,
        home_source="Vinnare semifinal A",
        away_source="Vinnare semifinal B",
        scheduled_start="2026-09-12T09:00",
        pitch_number=1,
    )
    assert structural_playoff_dependencies([final_only]) == {}
    analysis = analyze_schedule_conflicts([final_only], _rules())
    assert not [item for item in analysis["conflicts"] if item["type"] == "playoff_dependency"]


def test_bracket_identity_is_part_of_proposal_fingerprint():
    matches = [_match(1, 1, 1)]
    first = schedule_proposal_fingerprint(matches, _rules(), _windows())
    changed = [dict(matches[0], bracket_id=8)]
    second = schedule_proposal_fingerprint(changed, _rules(), _windows())
    assert first != second
