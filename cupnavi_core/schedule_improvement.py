"""Safe, preview-first schedule improvement for existing group schedules.

The optimizer only reassigns existing time/pitch/referee slots between eligible,
unplayed, unlocked group matches. It therefore preserves pitch utilization,
venue windows and referee occupancy. Teams with approved schedule requests or
late-start preferences are excluded from automatic movement.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from cupnavi_core.arrangement_type import ARRANGEMENT_MATCHCAMP, normalize_arrangement_type


def _team_id(source):
    text = str(source or "")
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _start(row):
    raw = row.get("scheduled_start")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def schedule_flow_metrics(
    matches,
    *,
    match_duration_minutes,
    minimum_rest_minutes,
    arrangement_type="tournament",
    long_wait_minutes=None,
):
    """Measure schedule flow using goals appropriate for the arrangement type.

    Matchcamp gives stronger weight to rest consistency and unnecessary waiting.
    Tournament remains more tolerant of longer waits because group/playoff
    structures can naturally create them. Structural metrics are returned too,
    but a slot-swap optimizer never pretends it can change match counts or
    opponents.
    """
    mode = normalize_arrangement_type(arrangement_type)
    duration_minutes = max(1, int(match_duration_minutes or 1))
    duration = timedelta(minutes=duration_minutes)
    wanted_rest = max(0, int(minimum_rest_minutes or 0))
    if long_wait_minutes is None:
        long_wait_minutes = 120 if mode == ARRANGEMENT_MATCHCAMP else 180

    by_team = {}
    opponents = {}
    direct_match_count = Counter()
    for row in matches:
        start = _start(row)
        home = _team_id(row.get("home_source"))
        away = _team_id(row.get("away_source"))
        if home is not None and away is not None:
            direct_match_count[home] += 1
            direct_match_count[away] += 1
            opponents.setdefault(home, []).append(away)
            opponents.setdefault(away, []).append(home)
        if start is None:
            continue
        for team_id in (home, away):
            if team_id is not None:
                by_team.setdefault(team_id, []).append(start)

    overlap = 0
    short_rest = 0
    long_waits = 0
    team_min_rests = []
    maximum_wait = None
    for starts in by_team.values():
        starts.sort()
        rests = []
        for a, b in zip(starts, starts[1:]):
            rest = int((b - (a + duration)).total_seconds() // 60)
            rests.append(rest)
            if rest < 0:
                overlap += 1
            elif rest < wanted_rest:
                short_rest += 1
            if rest > long_wait_minutes:
                long_waits += 1
            if maximum_wait is None or rest > maximum_wait:
                maximum_wait = rest
        if rests:
            team_min_rests.append(min(rests))

    fairness_spread = 0
    if len(team_min_rests) >= 2:
        fairness_spread = max(team_min_rests) - min(team_min_rests)
    minimum_actual_rest = min(team_min_rests) if team_min_rests else None

    counts = list(direct_match_count.values())
    match_count_spread = (max(counts) - min(counts)) if len(counts) >= 2 else 0
    playtime_spread_minutes = match_count_spread * duration_minutes
    repeated_opponents = sum(
        sum(max(0, count - 1) for count in Counter(team_opponents).values())
        for team_opponents in opponents.values()
    ) // 2

    if mode == ARRANGEMENT_MATCHCAMP:
        objective = (
            overlap * 100000
            + short_rest * 7000
            + long_waits * 1200
            + fairness_spread * 6
        )
        score = max(
            0,
            100
            - overlap * 40
            - short_rest * 14
            - long_waits * 7
            - min(24, fairness_spread // 8),
        )
    else:
        objective = overlap * 100000 + short_rest * 5000 + long_waits * 300 + fairness_spread
        score = max(
            0,
            100
            - overlap * 40
            - short_rest * 12
            - long_waits * 4
            - min(20, fairness_spread // 15),
        )

    return {
        "arrangement_type": mode,
        "overlap": overlap,
        "short_rest": short_rest,
        "long_waits": long_waits,
        "fairness_spread": fairness_spread,
        "minimum_actual_rest": minimum_actual_rest,
        "maximum_wait": maximum_wait,
        "match_count_spread": match_count_spread,
        "playtime_spread_minutes": playtime_spread_minutes,
        "repeated_opponents": repeated_opponents,
        "objective": objective,
        "score": score,
    }


def build_schedule_improvement(
    matches,
    *,
    match_duration_minutes,
    minimum_rest_minutes,
    protected_team_ids=(),
    arrangement_type="tournament",
    max_passes=8,
):
    """Return a deterministic, previewable slot-swap proposal.

    No database writes occur here. Only direct-team, scheduled, unplayed,
    unlocked group matches without protected teams are eligible.
    """
    protected = {int(x) for x in protected_team_ids or ()}
    mode = normalize_arrangement_type(arrangement_type)
    working = [dict(row) for row in matches]
    eligible = []
    for idx, row in enumerate(working):
        home = _team_id(row.get("home_source"))
        away = _team_id(row.get("away_source"))
        if (
            row.get("stage") == "Gruppspel"
            and row.get("scheduled_start")
            and not bool(row.get("schedule_locked"))
            and row.get("home_score") is None
            and row.get("away_score") is None
            and home is not None
            and away is not None
            and home not in protected
            and away not in protected
        ):
            eligible.append(idx)

    before = schedule_flow_metrics(
        working,
        match_duration_minutes=match_duration_minutes,
        minimum_rest_minutes=minimum_rest_minutes,
        arrangement_type=mode,
    )
    if len(eligible) < 2:
        return {
            "arrangement_type": mode,
            "before": before,
            "after": before,
            "updates": [],
            "eligible_count": len(eligible),
            "improved": False,
        }

    slot_keys = ("scheduled_start", "pitch_number", "referee_id")
    best_metric = before
    improved_any = False
    for _ in range(max(1, int(max_passes))):
        improved_this_pass = False
        for pos, i in enumerate(eligible):
            for j in eligible[pos + 1:]:
                old_i = tuple(working[i].get(k) for k in slot_keys)
                old_j = tuple(working[j].get(k) for k in slot_keys)
                for k, value in zip(slot_keys, old_j):
                    working[i][k] = value
                for k, value in zip(slot_keys, old_i):
                    working[j][k] = value
                metric = schedule_flow_metrics(
                    working,
                    match_duration_minutes=match_duration_minutes,
                    minimum_rest_minutes=minimum_rest_minutes,
                    arrangement_type=mode,
                )
                # Never introduce a team overlap; accept only strict objective improvement.
                if metric["overlap"] == 0 and metric["objective"] < best_metric["objective"]:
                    best_metric = metric
                    improved_this_pass = True
                    improved_any = True
                else:
                    for k, value in zip(slot_keys, old_i):
                        working[i][k] = value
                    for k, value in zip(slot_keys, old_j):
                        working[j][k] = value
        if not improved_this_pass:
            break

    original_by_id = {int(row["id"]): dict(row) for row in matches}
    updates = []
    if improved_any:
        for idx in eligible:
            row = working[idx]
            original = original_by_id[int(row["id"])]
            if any(row.get(k) != original.get(k) for k in slot_keys):
                updates.append({
                    "id": int(row["id"]),
                    "scheduled_start": row.get("scheduled_start"),
                    "pitch_number": row.get("pitch_number"),
                    "referee_id": row.get("referee_id"),
                })
    after = best_metric if improved_any else before
    return {
        "arrangement_type": mode,
        "before": before,
        "after": after,
        "updates": updates,
        "eligible_count": len(eligible),
        "improved": bool(updates) and after["objective"] < before["objective"],
    }
