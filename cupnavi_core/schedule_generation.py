"""Preview-first orchestration around CupNavi's existing schedule domain and optimizer.

This module does not persist anything. It assigns only eligible unplayed,
unlocked matches and treats already scheduled matches as fixed constraints.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from .schedule_domain import build_schedule_window, schedule_source_team_id
from .schedule_optimizer import optimize_match_order


def _parse_start(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _team_ids(match):
    return tuple(
        team_id
        for team_id in (
            schedule_source_team_id(match.get("home_source")),
            schedule_source_team_id(match.get("away_source")),
        )
        if team_id is not None
    )


def build_schedule_preview(matches, tournament, rules, *, referees=()):
    """Return deterministic proposed assignments without database writes.

    Existing scheduled matches, played matches and locked matches are preserved.
    Unscheduled eligible matches are ordered by the existing optimizer and placed
    in the earliest feasible pitch slot while respecting minimum team rest.
    """
    window = build_schedule_window(tournament, rules)
    pitch_count = max(1, int(rules.get("pitch_count") or 1))
    pitch_break = max(0, int(rules.get("pitch_break_minutes") or 0))
    minimum_rest = max(0, int(rules.get("minimum_team_rest_minutes") or 0))
    referee_ids = [int(r["id"]) for r in referees if r.get("id") is not None]

    fixed = []
    eligible = []
    for raw in matches:
        row = dict(raw)
        played = row.get("home_score") is not None or row.get("away_score") is not None
        locked = bool(row.get("schedule_locked") or 0)
        if row.get("scheduled_start") or played or locked:
            fixed.append(row)
        else:
            eligible.append(row)

    order, engine = optimize_match_order(eligible, pitch_count=pitch_count)
    by_id = {int(row["id"]): row for row in eligible}
    ordered = [by_id[int(match_id)] for match_id in order if int(match_id) in by_id]
    if len(ordered) != len(eligible):
        seen = {int(row["id"]) for row in ordered}
        ordered.extend(row for row in eligible if int(row["id"]) not in seen)

    pitch_free = {pitch: window.start for pitch in range(1, pitch_count + 1)}
    team_free = {}
    referee_free = {rid: window.start for rid in referee_ids}

    for row in fixed:
        start = _parse_start(row.get("scheduled_start"))
        pitch = row.get("pitch_number")
        if start is None:
            continue
        duration = window.duration_for_stage(row.get("stage"))
        end = start + duration
        try:
            pitch_no = int(pitch)
        except (TypeError, ValueError):
            pitch_no = None
        if pitch_no in pitch_free:
            pitch_free[pitch_no] = max(pitch_free[pitch_no], end + timedelta(minutes=pitch_break))
        for team_id in _team_ids(row):
            team_free[team_id] = max(team_free.get(team_id, window.start), end + timedelta(minutes=minimum_rest))
        rid = row.get("referee_id")
        if rid in referee_free:
            referee_free[rid] = max(referee_free[rid], end)

    updates = []
    unresolved = []
    current_date = window.start.date()

    def next_day_start(day):
        return datetime.combine(day, window.start.time())

    for row in ordered:
        duration = window.duration_for_stage(row.get("stage"))
        teams = _team_ids(row)
        best = None
        for pitch in range(1, pitch_count + 1):
            candidate = max(pitch_free[pitch], *(team_free.get(t, window.start) for t in teams))
            if candidate.date() < current_date:
                candidate = next_day_start(current_date)
            while candidate.date() <= window.end_date:
                if candidate.time() > window.latest_pitch_time:
                    candidate = next_day_start(candidate.date() + timedelta(days=1))
                    continue
                referee_id = None
                if referee_ids:
                    available = [rid for rid in referee_ids if referee_free.get(rid, window.start) <= candidate]
                    if not available:
                        next_ref = min(referee_free[rid] for rid in referee_ids)
                        candidate = max(candidate, next_ref)
                        continue
                    referee_id = min(available, key=lambda rid: (referee_free.get(rid, window.start), rid))
                option = (candidate, pitch, referee_id)
                if best is None or option[:2] < best[:2]:
                    best = option
                break
        if best is None:
            unresolved.append(int(row["id"]))
            continue
        start, pitch, referee_id = best
        end = start + duration
        pitch_free[pitch] = end + timedelta(minutes=pitch_break)
        for team_id in teams:
            team_free[team_id] = end + timedelta(minutes=minimum_rest)
        if referee_id is not None:
            referee_free[referee_id] = end
        updates.append({
            "id": int(row["id"]),
            "scheduled_start": start.isoformat(timespec="minutes"),
            "pitch_number": pitch,
            "referee_id": referee_id,
            "stage": row.get("stage"),
            "home_source": row.get("home_source"),
            "away_source": row.get("away_source"),
        })

    return {
        "engine": engine,
        "updates": updates,
        "unresolved_match_ids": unresolved,
        "unresolved_count": len(unresolved),
        "scheduled_count": len(updates),
        "preserved_count": len(fixed),
        "safe_to_apply": not unresolved and bool(updates),
    }
