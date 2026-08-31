"""UI-neutral helpers for CupNavi UX 2.0.

Keep decisions about hierarchy, progress and human-readable error IDs outside
Streamlit so a future frontend can reuse the same product logic.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

ADMIN_SECTIONS = [
    ("Översikt", ["Adminöversikt", "Cupinställningar"]),
    ("Deltagare", ["Lag", "Grupper", "Trupper", "Önskemålscentral", "Import"]),
    ("Matcher", ["Skapa och publicera schema", "Matcher och resultat", "Slutspel", "Matchhändelser", "Tabeller", "Skytteligor"]),
    ("Organisation", ["Domare", "Funktionärer", "Sponsorer", "Erbjudanden"]),
    ("Mer", []),
]


def workflow_progress(*, teams_ready: bool, groups_ready: bool, schedule_ready: bool, referees_ready: bool, published: bool) -> dict:
    steps = [
        ("Deltagare", teams_ready),
        ("Grupper", groups_ready),
        ("Schema", schedule_ready),
        ("Domare", referees_ready),
        ("Publicering", published),
    ]
    done = sum(1 for _label, ok in steps if ok)
    return {"done": done, "total": len(steps), "percent": round(done / len(steps) * 100), "steps": steps}


def attention_items(*, missing_referees: int = 0, unchecked_teams: int = 0, schedule_dirty: bool = False, unpublished: bool = False) -> list[dict]:
    items: list[dict] = []
    if schedule_dirty:
        items.append({"level": "critical", "text": "Schemat behöver uppdateras", "target": "Skapa och publicera schema"})
    if missing_referees:
        items.append({"level": "warning", "text": f"{missing_referees} matcher saknar domare", "target": "Domare"})
    if unchecked_teams:
        items.append({"level": "warning", "text": f"{unchecked_teams} lag/deltagare är inte incheckade", "target": "Lag"})
    if unpublished:
        items.append({"level": "info", "text": "Cupen är ännu inte publicerad", "target": "Kontroller"})
    return items


def human_error_id(exc: BaseException, prefix: str = "CN") -> str:
    payload = f"{type(exc).__name__}:{exc}:{datetime.utcnow().strftime('%Y%m%d%H')}".encode("utf-8", errors="replace")
    digest = hashlib.sha1(payload).hexdigest()[:6].upper()
    return f"{prefix}-{digest}"


def schedule_board(matches: list[dict], team_label) -> dict:
    """Return a time × pitch board usable by any frontend."""
    board: dict[str, dict[int, dict]] = {}
    pitches: set[int] = set()
    for row in matches:
        start = str(row.get("scheduled_start") or "")
        if not start:
            continue
        try:
            time_label = datetime.fromisoformat(start).strftime("%H:%M")
        except ValueError:
            time_label = start[-5:]
        pitch = int(row.get("pitch_number") or 0)
        pitches.add(pitch)
        board.setdefault(time_label, {})[pitch] = {
            "id": row.get("id"),
            "home": team_label(row.get("home_source")),
            "away": team_label(row.get("away_source")),
        }
    return {"times": sorted(board), "pitches": sorted(pitches), "cells": board}
