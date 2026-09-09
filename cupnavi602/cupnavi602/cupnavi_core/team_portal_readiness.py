"""Pure readiness helpers for the team portal match-day checklist."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Mapping


def _value(row, key, default=None):
    try:
        value = row[key]
    except (KeyError, TypeError, IndexError):
        try:
            value = row.get(key, default)
        except AttributeError:
            value = default
    return default if value is None and default is not None else value


def _is_future_match(row, *, now: datetime) -> bool:
    raw = _value(row, "scheduled_start")
    if not raw:
        return False
    try:
        return datetime.fromisoformat(str(raw)) >= now
    except (TypeError, ValueError):
        return False


def build_team_portal_readiness(
    team_row: Mapping[str, Any],
    *,
    players: Iterable[Mapping[str, Any]],
    team_matches: Iterable[Mapping[str, Any]],
    roster_rows: Iterable[Mapping[str, Any]],
    enable_team_checkin: bool,
    now: datetime,
) -> dict[str, Any]:
    """Return one simple checklist without mutating team/cup data.

    Match-roster readiness concerns future scheduled matches only. If no future
    matches exist yet, that item is intentionally waiting rather than failed.
    """
    players = list(players or [])
    team_matches = list(team_matches or [])
    roster_rows = list(roster_rows or [])

    rostered_match_ids = {
        int(_value(row, "match_id"))
        for row in roster_rows
        if _value(row, "match_id") is not None
    }
    future_matches = [row for row in team_matches if _is_future_match(row, now=now)]
    missing_match_rosters = [
        row for row in future_matches
        if int(_value(row, "id", 0) or 0) not in rostered_match_ids
    ]

    items = []

    if enable_team_checkin:
        checked_in = bool(_value(team_row, "checked_in", 0))
        items.append({
            "key": "checkin",
            "label": "Incheckning",
            "state": "ready" if checked_in else "todo",
            "detail": "Laget är på plats." if checked_in else "Checka in laget när ni anländer.",
            "tab": "Lag & matcher",
        })
    else:
        items.append({
            "key": "checkin",
            "label": "Incheckning",
            "state": "not_applicable",
            "detail": "Används inte i den här cupen.",
            "tab": "Lag & matcher",
        })

    kit_ready = bool(_value(team_row, "kit_confirmed_at", None))
    items.append({
        "key": "kit",
        "label": "Matchställ",
        "state": "ready" if kit_ready else "todo",
        "detail": "Matchställen är bekräftade." if kit_ready else "Bekräfta lagets matchställ.",
        "tab": "Lag & matcher",
    })

    roster_ready = len(players) > 0
    items.append({
        "key": "roster",
        "label": "Trupp",
        "state": "ready" if roster_ready else "todo",
        "detail": f"{len(players)} spelare registrerade." if roster_ready else "Registrera lagets spelare.",
        "tab": "Trupp",
    })

    if not future_matches:
        match_roster_state = "waiting"
        match_roster_detail = "Väntar på kommande spelschema."
    elif not missing_match_rosters:
        match_roster_state = "ready"
        match_roster_detail = f"Matchtrupp klar för {len(future_matches)} kommande match(er)."
    else:
        match_roster_state = "todo"
        match_roster_detail = (
            f"{len(missing_match_rosters)} av {len(future_matches)} kommande match(er) saknar matchtrupp."
        )
    items.append({
        "key": "match_rosters",
        "label": "Matchtrupper",
        "state": match_roster_state,
        "detail": match_roster_detail,
        "tab": "Matchtrupper",
        "missing_count": len(missing_match_rosters),
        "future_count": len(future_matches),
    })

    actionable = [item for item in items if item["state"] not in {"not_applicable", "waiting"}]
    ready_count = sum(1 for item in actionable if item["state"] == "ready")
    todo = [item for item in actionable if item["state"] == "todo"]

    return {
        "items": items,
        "ready_count": ready_count,
        "actionable_count": len(actionable),
        "todo_count": len(todo),
        "ready": bool(actionable) and not todo,
        "next_item": todo[0] if todo else None,
    }


def readiness_icon(state: str) -> str:
    return {
        "ready": "✅",
        "todo": "○",
        "waiting": "⏳",
        "not_applicable": "–",
    }.get(str(state), "○")
