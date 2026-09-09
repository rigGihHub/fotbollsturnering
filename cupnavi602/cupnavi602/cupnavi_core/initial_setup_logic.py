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


def setup_consequence_preview(*, team_count, total_matches, match_minutes, available_minutes):
    """Return a plain-language capacity preview for the setup handoff.

    The helper deliberately reports pitch-time demand rather than pretending to
    know the final schedule duration before the schedule engine has run.
    """
    teams=max(0,int(team_count or 0))
    matches=max(0,int(total_matches or 0))
    slot=max(1,int(match_minutes or 1))
    available=max(0,int(available_minutes or 0))
    demand=matches*slot
    utilization=(demand/available) if available else None
    if utilization is None:
        margin_label="Plantid saknas"
        margin_tone="unknown"
    elif utilization <= 0.75:
        margin_label="God marginal"
        margin_tone="good"
    elif utilization <= 0.90:
        margin_label="Rimlig marginal"
        margin_tone="ok"
    elif utilization <= 1.0:
        margin_label="Tajt marginal"
        margin_tone="tight"
    else:
        margin_label="Ryms inte i angiven plantid"
        margin_tone="over"
    return {
        "team_count": teams,
        "total_matches": matches,
        "pitch_time_minutes": demand,
        "available_minutes": available,
        "utilization": utilization,
        "utilization_percent": round(utilization*100) if utilization is not None else None,
        "margin_label": margin_label,
        "margin_tone": margin_tone,
    }
