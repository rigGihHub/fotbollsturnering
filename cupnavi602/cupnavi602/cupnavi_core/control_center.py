"""Operational control-center calculations for live tournaments."""
from __future__ import annotations
from datetime import datetime

def control_center_snapshot(matches, *, unread_messages=0, schedule_dirty=False, now=None):
    now = now or datetime.now()
    playing = upcoming = missing_results = delayed = 0
    for m in matches:
        start_raw = m.get("scheduled_start") if hasattr(m, "get") else None
        try:
            start = datetime.fromisoformat(str(start_raw)) if start_raw else None
        except ValueError:
            start = None
        home = m.get("home_score") if hasattr(m, "get") else None
        away = m.get("away_score") if hasattr(m, "get") else None
        complete = home is not None and away is not None
        if start and start > now:
            upcoming += 1
        elif start and not complete:
            missing_results += 1
            # Conservative: only call it delayed after 90 minutes; sport-specific
            # duration can replace this later.
            if (now-start).total_seconds() > 90*60:
                delayed += 1
    problems = delayed + (1 if schedule_dirty else 0)
    return {
        "upcoming": upcoming, "missing_results": missing_results, "delayed": delayed,
        "unread_messages": int(unread_messages or 0), "schedule_dirty": bool(schedule_dirty),
        "problems": problems,
    }
