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


def build_matchday_readiness_advice(
    matches,
    *,
    now: datetime,
    team_checkins: dict[int, bool] | None = None,
    checkin_enabled: bool = False,
    referee_mode: str = "Manuell",
    upcoming_window_minutes: int = 30,
    max_items: int = 3,
):
    """Flag concrete pre-kickoff readiness risks without guessing unresolved teams.

    This is deliberately conservative: only direct ``team:<id>`` sources are used
    for check-in warnings, and referee warnings are shown only when CupNavi is in
    automatic referee mode. The helper never mutates cup data.
    """
    rows = list(matches or [])
    checkins = dict(team_checkins or {})
    window = timedelta(minutes=max(1, int(upcoming_window_minutes or 1)))
    alerts = []

    def direct_team_id(source):
        parts = str(source or "").split(":")
        if len(parts) == 2 and parts[0] == "team" and parts[1].isdigit():
            return int(parts[1])
        return None

    for row in rows:
        start = _start(row)
        if start is None or start < now or start - now > window or _played(row):
            continue
        status = normalize_match_status(_value(row, "match_status"), has_result=_played(row))
        if status in {MATCH_FINISHED, MATCH_LIVE, MATCH_HALFTIME}:
            continue

        match_id = int(_value(row, "id", 0) or 0)
        pitch = int(_value(row, "pitch_number", 0) or 0)
        minutes = max(0, int((start - now).total_seconds() // 60))

        if checkin_enabled:
            missing_team_ids = []
            for source in (_value(row, "home_source"), _value(row, "away_source")):
                team_id = direct_team_id(source)
                if team_id is not None and team_id in checkins and not bool(checkins[team_id]):
                    missing_team_ids.append(team_id)
            if missing_team_ids:
                alerts.append({
                    "kind": "team_not_checked_in",
                    "severity": "error" if minutes <= 15 else "warning",
                    "title": "Lag saknas inför avspark" if len(missing_team_ids) == 1 else "Lag saknas inför avspark",
                    "detail": (
                        f"Matchen på plan {pitch} startar om cirka {minutes} min, men "
                        f"{len(missing_team_ids)} deltagande lag är inte incheckat. "
                        "Kontrollera om laget är på plats innan schemat ändras."
                    ),
                    "match_id": match_id,
                    "pitch_number": pitch,
                    "minutes_until": minutes,
                    "team_ids": missing_team_ids,
                    "action": "open_team_checkin",
                })

        if str(referee_mode or "").strip().casefold() == "automatisk" and not _value(row, "referee_id"):
            alerts.append({
                "kind": "missing_referee",
                "severity": "error" if minutes <= 15 else "warning",
                "title": "Domare saknas inför avspark",
                "detail": (
                    f"Matchen på plan {pitch} startar om cirka {minutes} min men saknar domare. "
                    "Bemanna matchen innan den startas."
                ),
                "match_id": match_id,
                "pitch_number": pitch,
                "minutes_until": minutes,
                "action": "open_referees",
            })

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    kind_rank = {"team_not_checked_in": 0, "missing_referee": 1}
    alerts.sort(key=lambda item: (
        severity_rank.get(item.get("severity"), 9),
        int(item.get("minutes_until", 999)),
        kind_rank.get(item.get("kind"), 9),
        int(item.get("pitch_number", 999)),
        int(item.get("match_id", 999999)),
    ))
    return alerts[: max(1, int(max_items or 1))]


def build_team_no_show_impact_preview(
    matches,
    *,
    team_id: int,
    now: datetime,
    max_matches: int = 8,
):
    """Preview the operational impact if one direct team does not show up.

    The helper is deliberately read-only. It does not cancel matches, award
    walkovers or rebuild the schedule because those decisions depend on the
    competition rules and organiser confirmation. Instead it shows exactly
    which future matches/opponents are affected and recommends the least
    disruptive immediate action: keep the slots until the absence is confirmed.
    """
    target = int(team_id)

    def direct_team_id(source):
        parts = str(source or "").split(":")
        if len(parts) == 2 and parts[0] == "team" and parts[1].isdigit():
            return int(parts[1])
        return None

    affected = []
    opponent_ids = set()
    for row in matches or []:
        start = _start(row)
        if start is None or start < now or _played(row):
            continue
        status = normalize_match_status(_value(row, "match_status"), has_result=_played(row))
        if status in {MATCH_FINISHED, MATCH_LIVE, MATCH_HALFTIME}:
            continue
        home_id = direct_team_id(_value(row, "home_source"))
        away_id = direct_team_id(_value(row, "away_source"))
        if target not in {home_id, away_id}:
            continue
        opponent_id = away_id if home_id == target else home_id
        if opponent_id is not None:
            opponent_ids.add(opponent_id)
        affected.append({
            "match_id": int(_value(row, "id", 0) or 0),
            "scheduled_start": _value(row, "scheduled_start"),
            "pitch_number": int(_value(row, "pitch_number", 0) or 0),
            "home_source": _value(row, "home_source"),
            "away_source": _value(row, "away_source"),
            "opponent_team_id": opponent_id,
            "stage": _value(row, "stage", ""),
        })

    affected.sort(key=lambda row: (str(row.get("scheduled_start") or ""), int(row.get("pitch_number") or 0), int(row.get("match_id") or 0)))
    visible = affected[: max(1, int(max_matches or 1))]
    return {
        "team_id": target,
        "affected_matches": visible,
        "affected_match_count": len(affected),
        "affected_opponent_count": len(opponent_ids),
        "hidden_match_count": max(0, len(affected) - len(visible)),
        "recommended_action": "confirm_then_review",
        "recommendation_title": "Behåll tiderna tills frånvaron är bekräftad",
        "recommendation_detail": (
            "Det stör övriga lag minst. Bekräfta först att laget verkligen uteblir; "
            "därefter kan arrangören besluta om walkover, inställd match eller schemaändring enligt cupens regler."
        ),
    }


def build_referee_no_show_recovery_preview(
    matches,
    *,
    referee_id: int,
    candidate_referee_ids,
    now: datetime,
    match_duration_minutes: int,
    max_matches: int = 8,
):
    """Preview same-time referee replacements when one referee is unavailable.

    Read-only and deliberately conservative: kickoff times and pitches never move.
    A candidate is accepted only when their existing assignments do not overlap the
    affected match window. The greedy choice prefers the referee with the lightest
    remaining workload, which reduces disruption without pretending to optimise the
    full referee schedule.
    """
    target = int(referee_id)
    duration = timedelta(minutes=max(1, int(match_duration_minutes or 1)))
    rows = list(matches or [])
    candidate_ids = sorted({int(value) for value in (candidate_referee_ids or []) if int(value) != target})

    affected = []
    for row in rows:
        start = _start(row)
        if start is None or start < now or _played(row):
            continue
        status = normalize_match_status(_value(row, "match_status"), has_result=_played(row))
        if status in {MATCH_FINISHED, MATCH_LIVE, MATCH_HALFTIME}:
            continue
        if int(_value(row, "referee_id", 0) or 0) != target:
            continue
        affected.append(row)
    affected.sort(key=lambda row: (_start(row) or datetime.max, int(_value(row, "id", 0) or 0)))

    existing_by_ref = {candidate_id: [] for candidate_id in candidate_ids}
    workload = {candidate_id: 0 for candidate_id in candidate_ids}
    for row in rows:
        assigned = int(_value(row, "referee_id", 0) or 0)
        if assigned not in existing_by_ref:
            continue
        start = _start(row)
        if start is None or start < now or _played(row):
            continue
        existing_by_ref[assigned].append((start, start + duration, int(_value(row, "id", 0) or 0)))
        workload[assigned] += 1

    proposed_by_ref = {candidate_id: [] for candidate_id in candidate_ids}
    assignments = []
    unresolved = []
    for row in affected:
        start = _start(row)
        end = start + duration
        eligible = []
        for candidate_id in candidate_ids:
            busy = existing_by_ref[candidate_id] + proposed_by_ref[candidate_id]
            overlaps = any(start < busy_end and end > busy_start for busy_start, busy_end, _match_id in busy)
            if not overlaps:
                eligible.append(candidate_id)
        if not eligible:
            unresolved.append(int(_value(row, "id", 0) or 0))
            continue
        chosen = min(eligible, key=lambda candidate_id: (workload[candidate_id] + len(proposed_by_ref[candidate_id]), candidate_id))
        proposed_by_ref[chosen].append((start, end, int(_value(row, "id", 0) or 0)))
        assignments.append({
            "match_id": int(_value(row, "id", 0) or 0),
            "scheduled_start": _value(row, "scheduled_start"),
            "pitch_number": int(_value(row, "pitch_number", 0) or 0),
            "replacement_referee_id": chosen,
            "home_source": _value(row, "home_source"),
            "away_source": _value(row, "away_source"),
        })

    visible = assignments[: max(1, int(max_matches or 1))]
    return {
        "referee_id": target,
        "affected_match_count": len(affected),
        "replacement_count": len(assignments),
        "unresolved_count": len(unresolved),
        "assignments": visible,
        "hidden_assignment_count": max(0, len(assignments) - len(visible)),
        "unresolved_match_ids": unresolved,
        "recommended": bool(affected) and not unresolved,
        "recommendation_title": (
            "Behåll tider och planer – byt bara domare"
            if affected and not unresolved
            else "Behåll tiderna och lös de återstående domarluckorna manuellt"
        ),
        "recommendation_detail": (
            "Alla berörda matcher kan bemannas med lediga registrerade domare utan att flytta någon match."
            if affected and not unresolved
            else f"{len(assignments)} av {len(affected)} berörda matcher kan få ersättare utan schemaändring."
        ),
    }
