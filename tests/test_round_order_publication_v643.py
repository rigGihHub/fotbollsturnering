import pytest

from cupnavi_api import publish_reporting_repository as publication
from cupnavi_api.schedule_conflicts import analyze_schedule_conflicts


def _rules():
    return {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 0,
    }


def _match(match_id, round_no, start, *, group_id=1, pitch=1):
    return {
        "id": match_id,
        "group_id": group_id,
        "group_name": f"Grupp {group_id}",
        "stage": "group",
        "match_no": match_id,
        "round_no": round_no,
        "home_source": f"placeholder:home:{match_id}",
        "away_source": f"placeholder:away:{match_id}",
        "scheduled_start": start,
        "pitch_number": pitch,
    }


def test_manual_round_inversion_is_blocking_error():
    matches = [
        _match(1, 1, "2026-09-12T10:00", pitch=1),
        _match(2, 2, "2026-09-12T09:00", pitch=2),
    ]
    result = analyze_schedule_conflicts(matches, _rules())
    round_conflicts = [item for item in result["conflicts"] if item["type"] == "round_order"]
    assert len(round_conflicts) == 1
    assert round_conflicts[0]["severity"] == "error"
    assert round_conflicts[0]["lower_round"] == 1
    assert round_conflicts[0]["higher_round"] == 2
    assert result["error_count"] == 1
    assert result["ok"] is False


def test_equal_round_kickoffs_are_not_reported_as_inversion():
    matches = [
        _match(1, 1, "2026-09-12T09:00", pitch=1),
        _match(2, 2, "2026-09-12T09:00", pitch=2),
    ]
    result = analyze_schedule_conflicts(matches, _rules())
    assert not [item for item in result["conflicts"] if item["type"] == "round_order"]


def test_round_order_is_scoped_per_group():
    matches = [
        _match(1, 1, "2026-09-12T10:00", group_id=1, pitch=1),
        _match(2, 2, "2026-09-12T09:00", group_id=2, pitch=2),
    ]
    result = analyze_schedule_conflicts(matches, _rules())
    assert not [item for item in result["conflicts"] if item["type"] == "round_order"]


def test_publication_payload_turns_schedule_errors_into_blocker(monkeypatch):
    tournament = {"id": 7, "playoff_format": "semi_final", "schedule_dirty": 0}

    def fake_one(sql, params=()):
        if "SELECT * FROM tournaments" in sql:
            return dict(tournament)
        if "COUNT(*) AS count" in sql:
            return {"count": 4}
        raise AssertionError(f"Unexpected query: {sql}")

    monkeypatch.setattr(publication, "one", fake_one)
    monkeypatch.setattr(
        publication,
        "_schedule_publication_analysis",
        lambda tournament_id: {
            "ok": False,
            "conflict_count": 1,
            "error_count": 1,
            "warning_count": 0,
            "conflicts": [
                {
                    "type": "round_order",
                    "severity": "error",
                    "message": "Grupp A: rond 1 startar efter rond 2.",
                }
            ],
        },
    )

    payload = publication._publication_payload(7)
    assert payload["ready"] is False
    assert payload["schedule_conflict_analysis"]["error_count"] == 1
    assert "1 blockerande schemafel måste åtgärdas." in payload["blockers"]


def test_publish_is_rejected_when_schedule_has_blockers(monkeypatch):
    monkeypatch.setattr(publication, "_has_tournament_access", lambda account_id, tournament_id: True)
    monkeypatch.setattr(
        publication,
        "_publication_payload",
        lambda tournament_id: {
            "blockers": ["1 blockerande schemafel måste åtgärdas."],
            "ready": False,
        },
    )

    with pytest.raises(ValueError, match="blockerande schemafel"):
        publication.set_publication(1, 7, True)
