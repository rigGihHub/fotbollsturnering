"""Mobile-first operational snapshot for a live tournament day."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from cupnavi_core.match_status import MATCH_FINISHED, MATCH_HALFTIME, MATCH_LIVE, normalize_match_status
from typing import Any


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
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def _complete(row):
    return _value(row, "home_score") is not None and _value(row, "away_score") is not None


def build_cup_day_snapshot(
    matches,
    *,
    now=None,
    match_duration_minutes=45,
    reporting_grace_minutes=10,
    upcoming_window_minutes=45,
    require_results=False,
):
    """Classify today's scheduled matches without mutating tournament data.

    ``require_results`` keeps a finished match in the action queue until a score
    exists. Result-free matchcamps can still treat explicit finished status as complete.
    """
    now = now or datetime.now()
    duration = timedelta(minutes=max(1, int(match_duration_minutes or 1)))
    grace = timedelta(minutes=max(0, int(reporting_grace_minutes or 0)))
    upcoming_window = timedelta(minutes=max(1, int(upcoming_window_minutes or 1)))

    today_matches = []
    live = []
    upcoming = []
    start_overdue = []
    reporting_due = []
    completed = []
    by_pitch = defaultdict(list)

    for row in matches or []:
        start = _start(row)
        if start is None or start.date() != now.date():
            continue
        item = dict(row) if hasattr(row, "keys") else row
        today_matches.append(item)
        pitch = _value(row, "pitch_number")
        if pitch is not None:
            by_pitch[int(pitch)].append(item)

        try:
            has_explicit_status = "match_status" in row.keys()
        except AttributeError:
            has_explicit_status = isinstance(row, dict) and "match_status" in row
        explicit_status = normalize_match_status(
            _value(row, "match_status", None),
            has_result=_complete(row),
        )
        if explicit_status == MATCH_FINISHED:
            if require_results and not _complete(row):
                reporting_due.append(item)
            else:
                completed.append(item)
            continue
        if explicit_status in {MATCH_LIVE, MATCH_HALFTIME}:
            live.append(item)
            continue

        end = start + duration
        if not has_explicit_status:
            # Compatibility for old in-memory snapshots/tests. Real v371 DB rows
            # always carry match_status and are never silently called live.
            if start <= now <= end + grace:
                live.append(item)
            elif now > end + grace:
                reporting_due.append(item)
            elif now < start:
                upcoming.append(item)
        elif now > start:
            # v403: A match with explicit status "not_started" must not be called
            # a missing result the instant kickoff time passes. During the normal
            # match window the organiser needs a start action; only after the
            # expected duration + reporting grace do we escalate to result follow-up.
            if now <= end + grace:
                start_overdue.append(item)
            else:
                reporting_due.append(item)
        else:
            upcoming.append(item)

    today_matches.sort(key=lambda row: (_start(row) or datetime.max, int(_value(row, "pitch_number", 999) or 999)))
    live.sort(key=lambda row: _start(row) or datetime.max)
    upcoming.sort(key=lambda row: _start(row) or datetime.max)
    start_overdue.sort(key=lambda row: _start(row) or datetime.max)
    reporting_due.sort(key=lambda row: _start(row) or datetime.max)
    completed.sort(key=lambda row: _start(row) or datetime.max)

    next_window = [
        row for row in upcoming
        if (_start(row) - now) <= upcoming_window
    ]

    pitch_states = []
    for pitch, rows in sorted(by_pitch.items()):
        rows.sort(key=lambda row: _start(row) or datetime.max)
        current = next((row for row in rows if row in live), None)
        next_match = next((row for row in rows if _start(row) and _start(row) > now and not _complete(row)), None)
        overdue_starts = [row for row in rows if row in start_overdue]
        overdue = [row for row in rows if row in reporting_due]
        if current:
            current_status = normalize_match_status(_value(current, "match_status", None))
            status = "Paus" if current_status == MATCH_HALFTIME else "Spelar nu"
        elif overdue_starts:
            status = "Starttid passerad"
        elif overdue:
            status = "Resultat saknas"
        elif next_match:
            status = "Nästa match väntar"
        else:
            status = "Klar för dagen"
        pitch_states.append({
            "pitch_number": pitch,
            "status": status,
            "current": current,
            "next": next_match,
            "start_overdue_count": len(overdue_starts),
            "overdue_count": len(overdue),
        })

    attention = []
    if start_overdue:
        attention.append({
            "severity": "warning",
            "title": f"{len(start_overdue)} match(er) har passerat starttid",
            "detail": "Bekräfta att matchen har startat eller öppna matchen för att rätta status.",
            "target": "Cupdagen",
        })
    if reporting_due:
        attention.append({
            "severity": "error",
            "title": f"{len(reporting_due)} match(er) väntar på resultat",
            "detail": "Matchtiden inklusive rapporteringsmarginal har passerat.",
            "target": "Matcher och resultat",
        })
    if next_window:
        attention.append({
            "severity": "info",
            "title": f"{len(next_window)} match(er) startar inom {upcoming_window_minutes} min",
            "detail": "Kontrollera plan, lag och domare innan avspark.",
            "target": "Matcher och resultat",
        })

    return {
        "date": now.date().isoformat(),
        "today_total": len(today_matches),
        "live": live,
        "upcoming": upcoming,
        "next_window": next_window,
        "start_overdue": start_overdue,
        "reporting_due": reporting_due,
        "completed": completed,
        "pitch_states": pitch_states,
        "attention": attention,
        "progress": (len(completed) / len(today_matches)) if today_matches else 0.0,
    }


def match_time_label(row):
    start = _start(row)
    return start.strftime("%H:%M") if start else "–"


def minutes_until(row, *, now=None):
    now = now or datetime.now()
    start = _start(row)
    if not start:
        return None
    return int((start - now).total_seconds() // 60)



def cup_day_primary_guidance(snapshot, *, now=None):
    """Return one clear organizer action for the live-day home screen."""
    now = now or datetime.now()
    snapshot = snapshot or {}
    due = list(snapshot.get("reporting_due") or [])
    start_overdue = list(snapshot.get("start_overdue") or [])
    live = list(snapshot.get("live") or [])
    next_window = list(snapshot.get("next_window") or [])
    upcoming = list(snapshot.get("upcoming") or [])

    if due:
        count = len(due)
        return {
            "state": "action",
            "eyebrow": "Behöver åtgärd",
            "title": f"Rapportera {count} resultat" if count > 1 else "Rapportera resultatet",
            "detail": "Matchtiden och rapporteringsmarginalen har passerat.",
            "button": "Öppna resultat",
            "target": "Matcher och resultat",
        }
    if start_overdue:
        count = len(start_overdue)
        return {
            "state": "action",
            "eyebrow": "Starttid passerad",
            "title": f"Starta {count} matcher" if count > 1 else "Starta matchen",
            "detail": "Planerad avspark har passerat, men matchen står fortfarande som ej startad.",
            "button": "Visa matchen",
            "target": None,
        }
    if live:
        count = len(live)
        return {
            "state": "live",
            "eyebrow": "Just nu",
            "title": f"{count} matcher spelas" if count > 1 else "1 match spelas",
            "detail": "Följ matcherna här. Rapportera resultat när de är färdiga.",
            "button": "Öppna resultat",
            "target": "Matcher och resultat",
        }
    if next_window:
        first = next_window[0]
        mins = minutes_until(first, now=now)
        when = f"om {mins} min" if mins is not None and mins >= 0 else "snart"
        return {
            "state": "next",
            "eyebrow": "Nästa steg",
            "title": f"Nästa match startar {when}",
            "detail": "Kontrollera plan, lag och domare inför avspark.",
            "button": "Visa nästa matcher",
            "target": None,
        }
    if upcoming:
        first = upcoming[0]
        mins = minutes_until(first, now=now)
        when = f"om {mins} min" if mins is not None and mins >= 0 else "senare idag"
        return {
            "state": "calm",
            "eyebrow": "Lugnt just nu",
            "title": f"Nästa match {when}",
            "detail": "Inget akut kräver åtgärd.",
            "button": "Öppna schema",
            "target": "Skapa och publicera schema",
        }
    if snapshot.get("today_total"):
        return {
            "state": "done",
            "eyebrow": "Dagen är klar",
            "title": "Alla dagens matcher är färdigrapporterade",
            "detail": "Du kan gå vidare till tabeller, slutspel eller summering.",
            "button": "Öppna resultat",
            "target": "Matcher och resultat",
        }
    return {
        "state": "empty",
        "eyebrow": "Ingen cupaktivitet idag",
        "title": "Inga schemalagda matcher idag",
        "detail": "Cupdagen blir aktiv när matcher finns på dagens datum.",
        "button": "Öppna schema",
        "target": "Skapa och publicera schema",
    }
