"""Pure helpers for compact mobile presentation."""
from __future__ import annotations

from datetime import datetime


def mobile_match_preview(rows, *, now=None, limit=3):
    """Return the most useful compact match preview for a phone-sized portal."""
    rows = list(rows or [])
    if not rows:
        return []
    limit = max(1, int(limit or 1))
    now = now or datetime.now()
    now_key = now.isoformat(timespec="minutes")
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["scheduled_start"] or ""),
            int(row["pitch_number"] or 0),
            int(row["id"]),
        ),
    )
    upcoming = [
        row for row in ordered
        if str(row["scheduled_start"] or "") >= now_key
    ]
    if upcoming:
        return upcoming[:limit]
    return ordered[-limit:]
