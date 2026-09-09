
from cupnavi_core.initial_setup_logic import (
    available_pitch_minutes,
    estimated_capacity_slots,
    estimated_match_length_minutes,
)


def rv(row,key,default=None):
    try:
        value=row[key]
    except Exception:
        value=default
    return default if value is None and default is not None else value


def test_available_pitch_minutes_ignores_unconfirmed_and_invalid_windows():
    windows=[
        {"play_date":"2026-08-27","start_time":"09:00","end_time":"12:00","confirmed":1},
        {"play_date":"2026-08-27","start_time":"12:00","end_time":"14:00","confirmed":0},
        {"play_date":"bad","start_time":"09:00","end_time":"10:00","confirmed":1},
    ]
    assert available_pitch_minutes(windows,row_value=rv)==180


def test_match_length_matches_setup_semantics():
    rules={"halves":2,"minutes_per_half":20,"halftime_minutes":5,"pitch_break_minutes":5}
    assert estimated_match_length_minutes(rules,row_value=rv)==50


def test_capacity_slots_uses_same_engine_as_format_recommendation():
    windows=[
        {"play_date":"2026-08-27","start_time":"09:00","end_time":"14:00","confirmed":1},
        {"play_date":"2026-08-27","start_time":"09:00","end_time":"14:00","confirmed":1},
    ]
    rules={"halves":2,"minutes_per_half":20,"halftime_minutes":5,"pitch_break_minutes":5}
    minutes,slots=estimated_capacity_slots(windows,rules,row_value=rv)
    assert minutes==600
    assert slots==12
