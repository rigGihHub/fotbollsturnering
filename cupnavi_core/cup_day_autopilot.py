"""Conservative, preview-only operational advice for the live cup day."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from cupnavi_core.match_status import MATCH_FINISHED, MATCH_HALFTIME, MATCH_LIVE, normalize_match_status


def _value(row: Any, key: str, default=None):
    if row is None:
        return default
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _start(row):
    raw = _value(row, "scheduled_start")
    try:
        return datetime.fromisoformat(str(raw)) if raw else None
    except (TypeError, ValueError):
        return None


def _played(row):
    return _value(row, "home_score") is not None and _value(row, "away_score") is not None


def _active(row):
    status = normalize_match_status(_value(row, "match_status"), has_result=_played(row))
    return status in {MATCH_LIVE, MATCH_HALFTIME}


def estimate_pitch_delay_minutes(
    matches,
    *,
    now: datetime,
    match_duration_minutes: int,
    buffer_minutes: int = 0,
) -> dict[int, int]:
    """Estimate delay only from explicit live/paused matches.

    We deliberately do not infer a delay from an old scheduled time alone.
    """
    duration = timedelta(minutes=max(1, int(match_duration_minutes or 1)))
    buffer = timedelta(minutes=max(0, int(buffer_minutes or 0)))
    delays: dict[int, int] = {}
    for row in matches or []:
        if not _active(row):
            continue
        pitch = _value(row, "pitch_number")
        if pitch is None:
            continue
        planned_start = _start(row)
        actual_raw = _value(row, "actual_started_at")
        try:
            actual_start = datetime.fromisoformat(str(actual_raw)) if actual_raw else planned_start
        except (TypeError, ValueError):
            actual_start = planned_start
        if not planned_start or not actual_start:
            continue
        planned_end = planned_start + duration + buffer
        projected_end = actual_start + duration + buffer
        # If a match is still active beyond its projected end, use now as the
        # conservative earliest finish; otherwise actual-start slippage is enough.
        projected_end = max(projected_end, now) if now > projected_end else projected_end
        delay = max(0, int((projected_end - planned_end).total_seconds() // 60))
        if delay:
            delays[int(pitch)] = max(delays.get(int(pitch), 0), delay)
    return delays


def build_autopilot_advice(
    matches,
    *,
    now: datetime,
    match_duration_minutes: int,
    minimum_rest_minutes: int,
    resolve_team_id: Callable[[str], int | None],
    max_items: int = 3,
):
    """Return ranked operational suggestions. Never mutates schedule data."""
    rows = list(matches or [])
    delays = estimate_pitch_delay_minutes(
        rows,
        now=now,
        match_duration_minutes=match_duration_minutes,
    )
    advice = []

    for pitch, delay in sorted(delays.items(), key=lambda item: (-item[1], item[0])):
        future = [
            row for row in rows
            if int(_value(row, "pitch_number", 0) or 0) == pitch
            and _start(row) is not None
            and _start(row) > now
            and not _played(row)
        ]
        if not future:
            continue
        affected = len(future)
        advice.append({
            "kind": "pitch_delay",
            "severity": "warning" if delay < 15 else "error",
            "title": f"Plan {pitch} riskerar cirka {delay} min försening",
            "detail": (
                f"{affected} kommande match(er) på planen kan påverkas. "
                "Förhandsgranska en förskjutning innan du ändrar schemat."
            ),
            "pitch_number": pitch,
            "delay_minutes": delay,
            "affected_matches": affected,
            "action": "preview_delay",
        })

    # Look for a future match whose planned start gives too little rest after
    # a currently active match. This is a warning only; no automatic move.
    active_rows = [row for row in rows if _active(row)]
    future_rows = [row for row in rows if _start(row) and _start(row) > now and not _played(row)]
    for active in active_rows:
        active_teams = {
            resolve_team_id(_value(active, "home_source")),
            resolve_team_id(_value(active, "away_source")),
        } - {None}
        if not active_teams:
            continue
        planned_active_start = _start(active)
        if not planned_active_start:
            continue
        actual_raw = _value(active, "actual_started_at")
        try:
            actual_start = datetime.fromisoformat(str(actual_raw)) if actual_raw else planned_active_start
        except (TypeError, ValueError):
            actual_start = planned_active_start
        projected_end = max(
            actual_start + timedelta(minutes=max(1, int(match_duration_minutes or 1))),
            now,
        )
        for nxt in future_rows:
            next_teams = {
                resolve_team_id(_value(nxt, "home_source")),
                resolve_team_id(_value(nxt, "away_source")),
            } - {None}
            shared = active_teams & next_teams
            if not shared:
                continue
            rest = int((_start(nxt) - projected_end).total_seconds() // 60)
            if rest < int(minimum_rest_minutes or 0):
                advice.append({
                    "kind": "rest_risk",
                    "severity": "error",
                    "title": "Viloperiod riskerar att bli för kort",
                    "detail": (
                        f"En pågående match påverkar nästa match för samma lag. "
                        f"Prognos: cirka {max(0, rest)} min vila mot kravet "
                        f"{int(minimum_rest_minutes or 0)} min."
                    ),
                    "match_id": int(_value(nxt, "id")),
                    "rest_minutes": rest,
                    "action": "review_schedule",
                })
                break

    # Deterministic priority: rest violations first, then largest pitch delay.
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    advice.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 9),
            -int(item.get("delay_minutes", 0)),
            int(item.get("pitch_number", 999)),
            int(item.get("match_id", 999999)),
        )
    )
    return advice[: max(1, int(max_items or 1))]
