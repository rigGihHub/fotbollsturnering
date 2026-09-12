"""Deterministic schedule conflict analysis for CupNavi.

The analyzer is intentionally pure: repositories provide scheduled matches and
competition rules, while this module only turns them into structured warnings.
That keeps conflict detection testable and reusable by schedule generation and
publication readiness.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from cupnavi_core.participant_sources import team_id_from_source
from .schedule_dependencies import schedule_dependencies


def _parse_start(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _team_id(source) -> int | None:
    return team_id_from_source(source)


def _match_ref(row: dict) -> dict:
    return {
        "match_id": int(row["id"]),
        "match_no": row.get("match_no"),
        "stage": row.get("stage"),
        "group_id": row.get("group_id"),
        "group_name": row.get("group_name"),
        "bracket_id": row.get("bracket_id"),
        "round_no": row.get("round_no"),
        "scheduled_start": row.get("scheduled_start"),
        "pitch_number": row.get("pitch_number"),
        "home_label": row.get("home_label"),
        "away_label": row.get("away_label"),
    }


def _group_round(row: dict) -> tuple[int, int] | None:
    try:
        group_id = int(row.get("group_id"))
        round_no = int(row.get("round_no"))
    except (TypeError, ValueError):
        return None
    if round_no <= 0:
        return None
    return group_id, round_no


def analyze_schedule_conflicts(matches: list[dict], rules: dict) -> dict:
    """Return deterministic conflicts for the currently scheduled matches."""
    halves = max(1, int(rules.get("halves") or 2))
    minutes_per_half = max(1, int(rules.get("minutes_per_half") or 20))
    halftime_minutes = max(0, int(rules.get("halftime_minutes") or 0))
    match_minutes = halves * minutes_per_half + max(0, halves - 1) * halftime_minutes
    pitch_break_minutes = max(0, int(rules.get("pitch_break_minutes") or 0))
    minimum_rest_minutes = max(0, int(rules.get("minimum_team_rest_minutes") or 0))

    prepared: list[tuple[datetime, dict]] = []
    parsed_start_by_id: dict[int, datetime] = {}
    conflicts: list[dict] = []
    rows_by_id = {int(row["id"]): row for row in matches if row.get("id") is not None}
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
        parsed_start_by_id[int(row["id"])] = start

    prepared.sort(key=lambda item: (item[0], int(item[1].get("pitch_number") or 0), int(item[1]["id"])))

    by_pitch: dict[int, list[tuple[datetime, dict]]] = {}
    by_team: dict[int, list[tuple[datetime, dict]]] = {}
    by_group: dict[int, list[tuple[datetime, int, dict]]] = {}
    for start, row in prepared:
        pitch = row.get("pitch_number")
        if pitch is not None:
            by_pitch.setdefault(int(pitch), []).append((start, row))
        for source in (row.get("home_source"), row.get("away_source")):
            team_id = _team_id(source)
            if team_id is not None:
                by_team.setdefault(team_id, []).append((start, row))
        group_round = _group_round(row)
        if group_round is not None:
            group_id, round_no = group_round
            by_group.setdefault(group_id, []).append((start, round_no, row))

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
    rest_span = timedelta(minutes=minimum_rest_minutes)
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

    for group_id, items in sorted(by_group.items()):
        items.sort(key=lambda item: (item[1], item[0], int(item[2]["id"])))
        for index, (start, round_no, row) in enumerate(items):
            for next_start, next_round, next_row in items[index + 1 :]:
                if next_round <= round_no:
                    continue
                if start <= next_start:
                    continue
                group_name = row.get("group_name") or next_row.get("group_name") or f"grupp {group_id}"
                conflicts.append(
                    {
                        "type": "round_order",
                        "severity": "error",
                        "group_id": group_id,
                        "lower_round": round_no,
                        "higher_round": next_round,
                        "match_ids": [int(row["id"]), int(next_row["id"])],
                        "message": f"{group_name}: rond {round_no} startar efter rond {next_round}.",
                        "matches": [_match_ref(row), _match_ref(next_row)],
                    }
                )

    # Canonical participant sources are authoritative. v644 bracket structure is
    # retained only as fallback for matches without explicit dependency sources.
    dependencies = schedule_dependencies(matches)
    for downstream_id, upstream_ids in sorted(dependencies.items()):
        downstream_start = parsed_start_by_id.get(downstream_id)
        if downstream_start is None or not upstream_ids:
            continue
        unscheduled = [upstream_id for upstream_id in upstream_ids if rows_by_id.get(upstream_id, {}).get("scheduled_start") in (None, "")]
        if unscheduled:
            involved = [downstream_id, *unscheduled]
            conflicts.append(
                {
                    "type": "playoff_dependency",
                    "severity": "error",
                    "downstream_match_id": downstream_id,
                    "upstream_match_ids": list(upstream_ids),
                    "match_ids": involved,
                    "message": "Slutspelsmatchen är schemalagd innan alla avgörande föregående matcher har fått en tid.",
                    "matches": [_match_ref(rows_by_id[mid]) for mid in involved if mid in rows_by_id],
                }
            )
            continue
        upstream_starts = [parsed_start_by_id.get(upstream_id) for upstream_id in upstream_ids]
        if any(start is None for start in upstream_starts):
            continue
        earliest = max(start + match_span + rest_span for start in upstream_starts if start is not None)
        if downstream_start < earliest:
            shortage = int((earliest - downstream_start).total_seconds() // 60)
            involved = [*upstream_ids, downstream_id]
            conflicts.append(
                {
                    "type": "playoff_dependency",
                    "severity": "error",
                    "downstream_match_id": downstream_id,
                    "upstream_match_ids": list(upstream_ids),
                    "match_ids": list(involved),
                    "earliest_start": earliest.isoformat(timespec="minutes"),
                    "shortage_minutes": shortage,
                    "message": f"Slutspelsmatchen startar {shortage} minuter för tidigt i förhållande till sina deltagarkällor och minsta vila.",
                    "matches": [_match_ref(rows_by_id[mid]) for mid in involved if mid in rows_by_id],
                }
            )

    type_order = {
        "invalid_start": 0,
        "pitch_overlap": 1,
        "team_overlap": 2,
        "insufficient_rest": 3,
        "round_order": 4,
        "playoff_dependency": 5,
    }
    conflicts.sort(
        key=lambda item: (
            type_order.get(item["type"], 99),
            tuple(item.get("match_ids") or []),
            int(item.get("pitch_number") or 0),
            int(item.get("team_id") or 0),
            int(item.get("group_id") or 0),
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
