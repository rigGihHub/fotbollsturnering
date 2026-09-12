"""Deterministic, review-first schedule proposals for existing CupNavi matches."""
from __future__ import annotations

from datetime import datetime, timedelta


def _team_id(source) -> int | None:
    text = str(source or "").strip()
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _start(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _duration_minutes(rules: dict) -> int:
    halves = max(1, int(rules.get("halves") or 2))
    per_half = max(1, int(rules.get("minutes_per_half") or 20))
    halftime = max(0, int(rules.get("halftime_minutes") or 0))
    return halves * per_half + max(0, halves - 1) * halftime


def _slots(windows: list[dict], rules: dict) -> list[tuple[datetime, int]]:
    """Build stable candidate kick-off slots.

    ``end_time`` follows the existing CupNavi venue model where default pitch
    windows are derived from ``latest_kickoff_time``. It is therefore treated as
    the latest allowed kick-off, not as the time the final match must finish.
    """
    step = timedelta(minutes=_duration_minutes(rules) + max(0, int(rules.get("pitch_break_minutes") or 0)))
    result: list[tuple[datetime, int]] = []
    for window in windows:
        try:
            pitch = int(window["pitch_number"])
            first = datetime.fromisoformat(f"{window['play_date']}T{window['start_time']}")
            last = datetime.fromisoformat(f"{window['play_date']}T{window['end_time']}")
        except (KeyError, TypeError, ValueError):
            continue
        current = first
        while current <= last:
            result.append((current, pitch))
            current += step
    return sorted(set(result), key=lambda item: (item[0], item[1]))


def _teams(row: dict) -> tuple[int, ...]:
    values = []
    for source in (row.get("home_source"), row.get("away_source")):
        team_id = _team_id(source)
        if team_id is not None and team_id not in values:
            values.append(team_id)
    return tuple(values)


def build_schedule_proposal(matches: list[dict], rules: dict, windows: list[dict]) -> dict:
    """Propose times/pitches without writing anything.

    Existing scheduled matches are fixed constraints. Played and locked matches
    are never moved. Unscheduled, unlocked and unplayed matches are placed in a
    deterministic round/group/match order. A placement is accepted only when it
    respects pitch occupancy and configured minimum team rest.
    """
    match_minutes = _duration_minutes(rules)
    pitch_break = max(0, int(rules.get("pitch_break_minutes") or 0))
    minimum_rest = max(0, int(rules.get("minimum_team_rest_minutes") or 0))
    match_span = timedelta(minutes=match_minutes)
    pitch_span = timedelta(minutes=match_minutes + pitch_break)
    rest_span = timedelta(minutes=minimum_rest)

    pitch_busy: dict[int, list[tuple[datetime, datetime]]] = {}
    team_busy: dict[int, list[tuple[datetime, datetime]]] = {}
    preserved = 0
    unresolved: list[dict] = []
    candidates: list[dict] = []

    for row in matches:
        start = _start(row.get("scheduled_start"))
        if start is not None and row.get("pitch_number") is not None:
            preserved += 1
            pitch = int(row["pitch_number"])
            pitch_busy.setdefault(pitch, []).append((start, start + pitch_span))
            for team_id in _teams(row):
                team_busy.setdefault(team_id, []).append((start, start + match_span))
            continue
        if bool(row.get("played")) or row.get("home_score") is not None or row.get("away_score") is not None:
            unresolved.append({"match_id": int(row["id"]), "reason": "played_without_schedule"})
            continue
        if bool(row.get("schedule_locked")):
            unresolved.append({"match_id": int(row["id"]), "reason": "locked_without_schedule"})
            continue
        candidates.append(row)

    candidates.sort(
        key=lambda row: (
            int(row.get("round_no") or 0),
            int(row.get("group_id") or 0),
            int(row.get("match_no") or 0),
            int(row["id"]),
        )
    )

    available_slots = _slots(windows, rules)
    placements: list[dict] = []
    for row in candidates:
        selected: tuple[datetime, int] | None = None
        for start, pitch in available_slots:
            pitch_end = start + pitch_span
            if any(start < busy_end and pitch_end > busy_start for busy_start, busy_end in pitch_busy.get(pitch, [])):
                continue
            match_end = start + match_span
            team_ok = True
            for team_id in _teams(row):
                for busy_start, busy_end in team_busy.get(team_id, []):
                    if start < busy_end + rest_span and match_end + rest_span > busy_start:
                        team_ok = False
                        break
                if not team_ok:
                    break
            if team_ok:
                selected = (start, pitch)
                break
        if selected is None:
            unresolved.append({"match_id": int(row["id"]), "reason": "no_feasible_slot"})
            continue
        start, pitch = selected
        pitch_busy.setdefault(pitch, []).append((start, start + pitch_span))
        for team_id in _teams(row):
            team_busy.setdefault(team_id, []).append((start, start + match_span))
        placements.append(
            {
                "match_id": int(row["id"]),
                "scheduled_start": start.isoformat(timespec="minutes"),
                "pitch_number": pitch,
            }
        )

    return {
        "deterministic": True,
        "writes_database": False,
        "match_duration_minutes": match_minutes,
        "pitch_break_minutes": pitch_break,
        "minimum_team_rest_minutes": minimum_rest,
        "preserved_count": preserved,
        "candidate_count": len(candidates),
        "placed_count": len(placements),
        "unresolved_count": len(unresolved),
        "placements": placements,
        "unresolved": sorted(unresolved, key=lambda item: item["match_id"]),
    }
