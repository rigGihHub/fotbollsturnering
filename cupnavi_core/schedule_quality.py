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
        except ValueError:
            unscheduled += 1
            continue
        for key in ("home_team_id","away_team_id"):
            team=m.get(key)
            if team is not None:
                by_team[int(team)].append(start)
        for key in ("home_team_id","away_team_id"):
            team=m.get(key)
            earliest=late_preferences.get(int(team)) if team is not None else None
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
