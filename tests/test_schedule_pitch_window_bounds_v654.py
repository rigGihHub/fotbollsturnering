from datetime import datetime, timedelta

from cupnavi_api.schedule_proposal import _duration_minutes, _slots


def _window(start="09:00", end="10:00"):
    return [{
        "pitch_number": 1,
        "play_date": "2026-09-13",
        "start_time": start,
        "end_time": end,
        "confirmed": 1,
    }]


def test_slots_never_allow_match_to_finish_after_pitch_window():
    rules = {
        "halves": 1,
        "minutes_per_half": 20,
        "halftime_minutes": 0,
        "pitch_break_minutes": 5,
    }

    slots = _slots(_window(), rules)

    assert [start.strftime("%H:%M") for start, _pitch in slots] == ["09:00", "09:25"]
    duration = timedelta(minutes=_duration_minutes(rules))
    window_end = datetime.fromisoformat("2026-09-13T10:00")
    assert all(start + duration <= window_end for start, _pitch in slots)


def test_slots_allow_match_to_finish_exactly_at_pitch_window_end():
    rules = {
        "halves": 1,
        "minutes_per_half": 30,
        "halftime_minutes": 0,
        "pitch_break_minutes": 0,
    }

    slots = _slots(_window(), rules)

    assert [start.strftime("%H:%M") for start, _pitch in slots] == ["09:00", "09:30"]
    assert slots[-1][0] + timedelta(minutes=30) == datetime.fromisoformat("2026-09-13T10:00")


def test_unconfirmed_default_window_is_never_used_for_a_real_proposal():
    rules = {"halves": 1, "minutes_per_half": 30, "halftime_minutes": 0, "pitch_break_minutes": 0}
    window = _window()
    window[0]["confirmed"] = 0

    assert _slots(window, rules) == []
