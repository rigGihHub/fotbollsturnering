"""Pure helpers for the initial tournament setup."""

from datetime import datetime


def available_pitch_minutes(windows, *, row_value):
    """Sum confirmed pitch-window minutes, ignoring invalid rows safely."""
    total=0
    for window in windows:
        if not bool(row_value(window,"confirmed",1)):
            continue
        try:
            start=datetime.fromisoformat(f"{window['play_date']}T{window['start_time']}")
            end=datetime.fromisoformat(f"{window['play_date']}T{window['end_time']}")
        except (KeyError,TypeError,ValueError):
            continue
        total += max(0,int((end-start).total_seconds()//60))
    return total


def estimated_match_length_minutes(rules, *, row_value):
    """Return one occupied pitch slot including periods and pitch break."""
    periods=max(1,int(row_value(rules,"halves",2) or 2))
    minutes=max(1,int(row_value(rules,"minutes_per_half",20) or 20))
    halftime=max(0,int(row_value(rules,"halftime_minutes",5) or 0))
    pitch_break=max(0,int(row_value(rules,"pitch_break_minutes",5) or 0))
    return max(1, periods*minutes + halftime + pitch_break)


def estimated_capacity_slots(windows, rules, *, row_value):
    minutes=available_pitch_minutes(windows,row_value=row_value)
    match_length=estimated_match_length_minutes(rules,row_value=row_value)
    return minutes, (minutes//match_length if minutes else 0)


def normalized_priority_order(saved, defaults):
    """Keep valid saved order and append new defaults exactly once."""
    saved = saved if isinstance(saved, list) else []
    return [x for x in saved if x in defaults] + [x for x in defaults if x not in saved]


def priority_order_changed(candidate, persisted):
    """True only when a real ordering change needs persistence."""
    return list(candidate or []) != list(persisted or [])
