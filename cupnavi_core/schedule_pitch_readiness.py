"""Read-only check shared by the schedule screen and its approval action."""
from __future__ import annotations

from datetime import datetime, timedelta

from .pitch_availability import expand_pitch_windows


def pitch_window_readiness(matches: list[dict], rules: dict, windows: list[dict]) -> dict:
    halves = max(1, int(rules.get("halves") or 2))
    duration = halves * max(1, int(rules.get("minutes_per_half") or 20))
    duration += max(0, halves - 1) * max(0, int(rules.get("halftime_minutes") or 0))
    available = {}
    for window in expand_pitch_windows([row for row in windows if row.get("confirmed")]):
        key = (int(window["pitch_number"]), str(window["play_date"]))
        available.setdefault(key, []).append((
            datetime.fromisoformat(f"{key[1]}T{window['start_time']}"),
            datetime.fromisoformat(f"{key[1]}T{window['end_time']}"),
        ))
    scheduled = {}
    issues = []
    for match in matches:
        if not match.get("scheduled_start"):
            continue
        match_ids = [int(match["id"])]
        if not match.get("pitch_number"):
            issues.append({"type": "missing_pitch", "message": f"Match {match.get('match_no') or match['id']} saknar plan. Ange planen under Schema.", "match_ids": match_ids})
            continue
        try:
            start = datetime.fromisoformat(str(match["scheduled_start"]))
            if start.tzinfo is not None:
                raise ValueError("Expected local kickoff time")
            end = start + timedelta(minutes=duration)
        except (ValueError, TypeError):
            issues.append({"type": "invalid_schedule", "message": f"Match {match.get('match_no') or match['id']} har en ogiltig avspark. Rätta tiden under Schema.", "match_ids": match_ids})
            continue
        key = (int(match["pitch_number"]), start.date().isoformat())
        scheduled.setdefault(key, []).append((match, start, end))
    requirements = []
    for (pitch, day), rows in sorted(scheduled.items()):
        first = min(start for _, start, _ in rows)
        last = max(end for _, _, end in rows)
        requirements.append({"pitch_number": pitch, "play_date": day, "first_start": first.isoformat(), "last_end": last.isoformat(), "match_count": len(rows)})
        intervals = available.get((pitch, day), [])
        outside = [match for match, start, end in rows if not any(start >= opens and end <= closes for opens, closes in intervals)]
        if not outside:
            continue
        if not intervals:
            text = f"Plan {pitch} den {day} saknar bekräftad öppettid."
            kind = "unconfirmed"
        else:
            text = f"Plan {pitch} den {day}: {len(outside)} matcher ligger utanför planens bekräftade öppettid."
            kind = "outside_window"
        closing = last.strftime('%H:%M') if last.date() == first.date() else last.strftime('%Y-%m-%d %H:%M')
        text += f" Schemat använder planen från {first:%H:%M} till {closing}, inklusive matchlängd. Kontrollera passen under Planer & tider."
        issues.append({"type": kind, "message": text, "pitch_number": pitch, "play_date": day, "match_ids": [int(match['id']) for match in outside]})
    return {"ready": not issues, "issues": issues, "requirements": requirements}
