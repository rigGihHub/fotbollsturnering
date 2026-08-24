from datetime import datetime
from pathlib import Path

from cupnavi_core.experience import (
    SPORT_PROFILES,
    analyze_schedule_change,
    planned_delay_updates,
    tournament_quality_score,
    cup_summary,
)


def _team(source):
    if not source or not source.startswith("team:"):
        return None
    return int(source.split(":")[1])


def test_multisport_profiles_cover_requested_sports():
    for sport in ["Fotboll", "Innebandy", "Handboll", "Ishockey", "Tennis"]:
        assert sport in SPORT_PROFILES
        assert SPORT_PROFILES[sport]["halves"] >= 1
        assert SPORT_PROFILES[sport]["minutes_per_half"] >= 1


def test_schedule_change_detects_pitch_referee_and_team_rest_conflicts():
    matches = [
        {
            "id": 1, "match_no": 1, "scheduled_start": "2026-08-24T10:00",
            "pitch_number": 1, "home_source": "team:1", "away_source": "team:2", "referee_id": 5,
        },
        {
            "id": 2, "match_no": 2, "scheduled_start": "2026-08-24T10:30",
            "pitch_number": 1, "home_source": "team:1", "away_source": "team:3", "referee_id": 5,
        },
    ]
    rules = {
        "halves": 2, "minutes_per_half": 20, "halftime_minutes": 5,
        "pitch_break_minutes": 5, "minimum_team_rest_minutes": 45,
    }
    issues = analyze_schedule_change(matches, 1, "2026-08-24T10:25", 1, rules, _team)
    codes = {issue["code"] for issue in issues}
    assert "pitch_overlap" in codes
    assert "referee_overlap" in codes
    assert "team_rest" in codes


def test_delay_updates_only_unplayed_matches_on_selected_pitch():
    matches = [
        {"id": 1, "pitch_number": 1, "scheduled_start": "2026-08-24T10:00", "home_score": None, "away_score": None},
        {"id": 2, "pitch_number": 1, "scheduled_start": "2026-08-24T11:00", "home_score": 2, "away_score": 1},
        {"id": 3, "pitch_number": 2, "scheduled_start": "2026-08-24T10:00", "home_score": None, "away_score": None},
    ]
    result = planned_delay_updates(matches, 1, 15)
    assert result == [(1, "2026-08-24T10:15")]


def test_quality_score_penalizes_incomplete_cup():
    tournament = {"name": "Testcup", "start_date": "2026-08-24", "schedule_dirty": 1}
    score, findings = tournament_quality_score(tournament, [], [], [], None)
    assert score < 60
    assert {item["code"] for item in findings} >= {"teams", "matches", "dirty"}


def test_cup_summary_counts_played_and_score():
    summary = cup_summary(
        {"name": "Cup", "sport": "Handboll"},
        [{"id": 1}, {"id": 2}],
        [
            {"home_score": 4, "away_score": 3},
            {"home_score": None, "away_score": None},
        ],
    )
    assert summary["sport"] == "Handboll"
    assert summary["teams"] == 2
    assert summary["played_matches"] == 1
    assert summary["total_score"] == 7


def test_v96_features_are_wired_into_streamlit_app():
    text = Path("app.py").read_text(encoding="utf-8")
    required = [
        "Min cup – följ ett lag",
        "notifications",
        "CupNavi Score",
        "Digital lagincheckning",
        "Domarcentral",
        "Automatisk matchförsening",
        "Slutspelsprognos",
        "Cupkarta",
        "QR-koder per plan",
        "Vad händer om jag flyttar en match?",
        "CupNavi-kvalitet",
        "Ändringshistorik och ångra",
        "Publikt cupflöde",
        "localStorage",
        "Automatisk cupsummering",
    ]
    for marker in required:
        assert marker in text


def test_v96_schema_migration_contains_experience_tables():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 5" in text
    for table in ["audit_log", "cup_feed", "notifications", "venue_points", "referee_acknowledgements"]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in text
    assert "ADD COLUMN sport" in text
    assert "ADD COLUMN checked_in" in text
