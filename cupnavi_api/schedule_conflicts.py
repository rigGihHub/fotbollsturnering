"""Deterministic schedule conflict analysis for CupNavi.

The analyzer is intentionally pure: repositories provide scheduled matches and
competition rules, while this module only turns them into structured warnings.
That keeps conflict detection testable and reusable by future schedule generators.
"""
from __future__ import annotations

from datetime import datetime, timedelta


def _parse_start(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _team_id(source) -> int | None:
    text = str(source or "").strip()
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _match_ref(row: dict) -> dict:
    return {
        "match_id": int(row["id"]),
        "match_no": row.get("match_no"),
        "stage": row.get("stage"),
        "scheduled_start": row.get("scheduled_start"),
        "pitch_number": row.get("pitch_number"),
        "home_label": row.get("home_label"),
        "away_label": row.get("away_label"),
    }


def analyze_schedule_conflicts(matches: list[dict], rules: dict) -> dict:
    """Return deterministic conflicts for the currently scheduled matches.

    Conflict types:
    - invalid_start: a non-empty start value could not be parsed.
    - pitch_overlap: a pitch is reused before match + configured pitch break ends.
    - team_overlap: a known team is scheduled before its previous match ends.
    - insufficient_rest: a known team gets less than configured minimum rest.

    Only explicit ``team:<id>`` participants are evaluated for team conflicts.
    Placeholder playoff/group sources are deliberately ignored until resolved so
    CupNavi does not report conflicts for participants that are not known yet.
    """
    halves = max(1, int(rules.get("halves") or 2))
    minutes_per_half = max(1, int(rules.get("minutes_per_half") or 20))
    halftime_minutes = max(0, int(rules.get("halftime_minutes") or 0))
    match_minutes = halves * minutes_per_half + max(0, halves - 1) * halftime_minutes
    pitch_break_minutes = max(0, int(rules.get("pitch_break_minutes") or 0))
    minimum_rest_minutes = max(0, int(rules.get("minimum_team_rest_minutes") or 0))

    prepared: list[tuple[datetime, dict]] = []
    conflicts: list[dict] = []
    for row in matches:
        raw_start = row.get("scheduled_start")
        if raw_start in (None, ""):
            continue
        start = _parse_start(raw_start)
        if start is None:
            conflicts.append(
                {
                    "type": "invalid_start",
                    "severity": "error",
                    "match_ids": [int(row["id"])],
                    "message": "Matchen har en ogiltig starttid.",
                    "match": _match_ref(row),
                }
            )
            continue
        prepared.append((start, row))

    prepared.sort(key=lambda item: (item[0], int(item[1].get("pitch_number") or 0), int(item[1]["id"])))

    by_pitch: dict[int, list[tuple[datetime, dict]]] = {}
    by_team: dict[int, list[tuple[datetime, dict]]] = {}
    for start, row in prepared:
        pitch = row.get("pitch_number")
        if pitch is not None:
            by_pitch.setdefault(int(pitch), []).append((start, row))
        for source in (row.get("home_source"), row.get("away_source")):
            team_id = _team_id(source)
            if team_id is not None:
                by_team.setdefault(team_id, []).append((start, row))

    pitch_span = timedelta(minutes=match_minutes + pitch_break_minutes)
    for pitch, items in sorted(by_pitch.items()):
        for index, (start, row) in enumerate(items):
            occupied_until = start + pitch_span
            for next_start, next_row in items[index + 1 :]:
                if next_start >= occupied_until:
                    break
                conflicts.append(
                    {
                        "type": "pitch_overlap",
                        "severity": "error",
                        "pitch_number": pitch,
                        "match_ids": [int(row["id"]), int(next_row["id"])],
                        "overlap_minutes": int((occupied_until - next_start).total_seconds() // 60),
                        "message": f"Plan {pitch} är dubbelbokad eller saknar planpaus.",
                        "matches": [_match_ref(row), _match_ref(next_row)],
                    }
                )

    match_span = timedelta(minutes=match_minutes)
    for team_id, items in sorted(by_team.items()):
        items.sort(key=lambda item: (item[0], int(item[1]["id"])))
        for index, (start, row) in enumerate(items):
            match_end = start + match_span
            for next_start, next_row in items[index + 1 :]:
                rest_minutes = int((next_start - match_end).total_seconds() // 60)
                if rest_minutes >= minimum_rest_minutes:
                    break
                conflict_type = "team_overlap" if rest_minutes < 0 else "insufficient_rest"
                severity = "error" if rest_minutes < 0 else "warning"
                message = (
                    "Samma lag är schemalagt i två överlappande matcher."
                    if rest_minutes < 0
                    else f"Laget får bara {rest_minutes} minuters vila; minst {minimum_rest_minutes} krävs."
                )
                conflicts.append(
                    {
                        "type": conflict_type,
                        "severity": severity,
                        "team_id": team_id,
                        "match_ids": [int(row["id"]), int(next_row["id"])],
                        "rest_minutes": rest_minutes,
                        "required_rest_minutes": minimum_rest_minutes,
                        "message": message,
                        "matches": [_match_ref(row), _match_ref(next_row)],
                    }
                )

    type_order = {"invalid_start": 0, "pitch_overlap": 1, "team_overlap": 2, "insufficient_rest": 3}
    conflicts.sort(
        key=lambda item: (
            type_order.get(item["type"], 99),
            tuple(item.get("match_ids") or []),
            int(item.get("pitch_number") or 0),
            int(item.get("team_id") or 0),
        )
    )
    error_count = sum(1 for item in conflicts if item["severity"] == "error")
    warning_count = sum(1 for item in conflicts if item["severity"] == "warning")
    return {
        "ok": error_count == 0 and warning_count == 0,
        "conflict_count": len(conflicts),
        "error_count": error_count,
        "warning_count": warning_count,
        "match_duration_minutes": match_minutes,
        "pitch_break_minutes": pitch_break_minutes,
        "minimum_team_rest_minutes": minimum_rest_minutes,
        "conflicts": conflicts,
    }
