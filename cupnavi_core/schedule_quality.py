"""Transparent schedule quality score; no fake AI confidence."""
from __future__ import annotations

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
