from datetime import timedelta

import pytest

from cupnavi_core.schedule_domain import (
    build_schedule_window,
    schedule_source_team_id,
)


def rules():
    return {
        "first_match_time": "09:00",
        "latest_kickoff_time": "18:00",
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
    }


def tournament():
    return {
        "start_date": "2026-08-21",
        "end_date": "2026-08-22",
        "tournament_date": "2026-08-21",
        "playoff_tie_rule": "Förlängning + straffar",
        "extra_time_minutes": 10,
    }


def test_schedule_window_calculates_durations():
    window = build_schedule_window(tournament(), rules())
    assert window.group_match_duration == timedelta(minutes=45)
    assert window.duration_for_stage("Gruppspel") == timedelta(minutes=45)
    assert window.duration_for_stage("Final") == timedelta(minutes=55)
    assert window.start.isoformat() == "2026-08-21T09:00:00"
    assert str(window.latest_pitch_time) == "18:00:00"


def test_invalid_match_duration_rejected():
    bad = rules()
    bad["minutes_per_half"] = 0
    with pytest.raises(ValueError):
        build_schedule_window(tournament(), bad)


def test_source_team_id_only_accepts_direct_team_source():
    assert schedule_source_team_id("team:42") == 42
    assert schedule_source_team_id("winner:7") is None
    assert schedule_source_team_id(None) is None
