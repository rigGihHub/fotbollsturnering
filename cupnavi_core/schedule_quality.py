"""Transparent CupNavi schedule quality scoring.

This is deterministic decision support, not an AI probability.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime

def schedule_quality_score(*, unscheduled: int, short_rest: int, travel_conflicts: int,
                           late_preferences_missed: int, color_warnings: int) -> dict:
    penalties = {
        "capacity": min(60, max(0, unscheduled) * 20),
        "rest": min(25, max(0, short_rest) * 5),
        "travel": min(25, max(0, travel_conflicts) * 5),
        "preferences": min(15, max(0, late_preferences_missed) * 3),
        "colors": min(10, max(0, color_warnings)),
    }
    score = max(0, 100 - sum(penalties.values()))
    return {"score": score, "penalties": penalties,
            "grade": "Mycket bra" if score >= 90 else "Bra" if score >= 75 else "Behöver förbättras" if score >= 50 else "Kritisk"}

def _source_team_id(value):
    """Resolve direct team sources without touching the database.

    Group/winner/loser placeholders intentionally return None because their team
    is not stable until competition results resolve them.
    """
    text=str(value or "")
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":",1)[1])
    except (TypeError,ValueError):
        return None

def _match_team_ids(match):
    # Legacy keys are accepted for backwards-compatible tests/imports.
    home=match.get("home_team_id")
    away=match.get("away_team_id")
    if home is None:
        home=_source_team_id(match.get("home_source"))
    if away is None:
        away=_source_team_id(match.get("away_source"))
    return home,away

def assess_schedule(matches, *, min_rest_minutes=0, late_preferences=None):
    late_preferences = late_preferences or {}
    unscheduled=0
    short_rest=0
    late_missed=0
    by_team=defaultdict(list)
    for m in matches:
        start_raw=m.get("scheduled_start")
        if not start_raw:
            unscheduled += 1
            continue
        try:
            start=datetime.fromisoformat(str(start_raw))
        except (TypeError,ValueError):
            unscheduled += 1
            continue

        home_team,away_team=_match_team_ids(m)
        for team in (home_team,away_team):
            if team is not None:
                by_team[int(team)].append(start)
                earliest=late_preferences.get(int(team))
                if earliest and start.strftime("%H:%M") < str(earliest):
                    late_missed += 1

    if min_rest_minutes > 0:
        for starts in by_team.values():
            starts.sort()
            for a,b in zip(starts,starts[1:]):
                if (b-a).total_seconds()/60 < min_rest_minutes:
                    short_rest += 1
    result=schedule_quality_score(unscheduled=unscheduled,short_rest=short_rest,travel_conflicts=0,
                                  late_preferences_missed=late_missed,color_warnings=0)
    result.update({"unscheduled":unscheduled,"short_rest":short_rest,
                   "late_preferences_missed":late_missed})
    return result


def _grade_dimension(score):
    score = max(0, min(100, int(round(score))))
    if score >= 90:
        return "Mycket bra"
    if score >= 75:
        return "Bra"
    if score >= 55:
        return "Okej"
    return "Behöver förbättras"


def schedule_quality_dimensions(
    matches,
    *,
    min_rest_minutes=0,
    match_duration_minutes=0,
    long_wait_minutes=150,
):
    """Explain schedule quality in organizer-facing dimensions.

    This deliberately avoids a second overall score. CupNavi already has a
    0–100 Schema Score; these dimensions explain *why* the schedule feels good
    or bad using transparent, deterministic thresholds.
    """
    total = len(matches or [])
    scheduled = []
    by_team = defaultdict(list)
    by_pitch = defaultdict(list)

    for match in matches or []:
        raw = match.get("scheduled_start") if isinstance(match, dict) else match["scheduled_start"]
        if not raw:
            continue
        try:
            start = datetime.fromisoformat(str(raw))
        except (TypeError, ValueError):
            continue
        scheduled.append(start)
        pitch = match.get("pitch_number") if isinstance(match, dict) else match["pitch_number"]
        if pitch is not None:
            by_pitch[int(pitch)].append(start)
        home, away = _match_team_ids(match)
        for team_id in (home, away):
            if team_id is not None:
                by_team[int(team_id)].append(start)

    scheduled_n = len(scheduled)
    completeness_score = 100 if total == 0 else 100 * scheduled_n / total
    unscheduled = max(0, total - scheduled_n)

    short_rests = 0
    long_waits = 0
    min_rest_by_team = []
    team_span_minutes = []
    for starts in by_team.values():
        starts.sort()
        if len(starts) >= 2:
            rests = [int((b - a).total_seconds() // 60) for a, b in zip(starts, starts[1:])]
            if min_rest_minutes > 0:
                short_rests += sum(1 for rest in rests if rest < min_rest_minutes)
            long_waits += sum(1 for rest in rests if rest > long_wait_minutes)
            min_rest_by_team.append(min(rests))
            team_span_minutes.append(int((starts[-1] - starts[0]).total_seconds() // 60))

    rest_score = max(0, 100 - short_rests * 18)
    flow_score = max(0, 100 - long_waits * 10)

    fairness_penalty = 0
    fairness_detail = "För få matcher för att jämföra lagen."
    if len(min_rest_by_team) >= 2:
        spread = max(min_rest_by_team) - min(min_rest_by_team)
        if spread > 90:
            fairness_penalty += 30
        elif spread > 45:
            fairness_penalty += 15
        if len(team_span_minutes) >= 2:
            span_spread = max(team_span_minutes) - min(team_span_minutes)
            if span_spread > 180:
                fairness_penalty += 25
            elif span_spread > 90:
                fairness_penalty += 12
        fairness_detail = f"Skillnaden i kortaste vila mellan lagen är {spread} min."
    fairness_score = max(0, 100 - fairness_penalty)

    # Utilization is descriptive, not a hard correctness rule. A lower value may
    # be intentional when the organizer prioritizes rest or travel.
    utilization_values = []
    expected_slot = max(1, int(match_duration_minutes or 0))
    for starts in by_pitch.values():
        starts.sort()
        if len(starts) < 2:
            continue
        observed_span = max(1, int((starts[-1] - starts[0]).total_seconds() // 60) + expected_slot)
        active = len(starts) * expected_slot
        utilization_values.append(min(100, 100 * active / observed_span))
    utilization = round(sum(utilization_values) / len(utilization_values)) if utilization_values else (100 if scheduled_n else 0)

    return {
        "completeness": {
            "score": round(completeness_score),
            "grade": _grade_dimension(completeness_score),
            "detail": "Alla matcher är schemalagda." if unscheduled == 0 else f"{unscheduled} matcher saknar tid.",
        },
        "rest": {
            "score": round(rest_score),
            "grade": _grade_dimension(rest_score),
            "detail": (
                "Ingen för kort lagvila hittades."
                if short_rests == 0
                else f"{short_rests} tillfällen underskrider minsta lagvilan."
            ),
        },
        "flow": {
            "score": round(flow_score),
            "grade": _grade_dimension(flow_score),
            "detail": (
                f"Inga lagväntetider över {long_wait_minutes} min."
                if long_waits == 0
                else f"{long_waits} väntetider över {long_wait_minutes} min."
            ),
        },
        "fairness": {
            "score": round(fairness_score),
            "grade": _grade_dimension(fairness_score),
            "detail": fairness_detail,
        },
        "pitch_utilization": {
            "score": utilization,
            "grade": _grade_dimension(utilization),
            "detail": (
                f"Planerna används cirka {utilization}% av den observerade schematiden. "
                "Lägre utnyttjande kan vara avsiktligt för mer vila."
            ),
        },
    }
