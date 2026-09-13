"""Review-first import of pitch opening windows extracted from cup documents."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _snapshot(tournament_id: int) -> dict:
    row = one(
        """SELECT payload_json,source_name FROM tournament_setup_imports
           WHERE tournament_id=? AND import_kind='initial_setup'
           ORDER BY id DESC LIMIT 1""",
        (int(tournament_id),),
    )
    if not row:
        return {}
    try:
        payload = json.loads(str(row.get("payload_json") or "{}"))
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    payload.setdefault("source_name", row.get("source_name"))
    return payload


def _cup_dates(tournament: dict) -> set[str]:
    start_raw = tournament.get("start_date") or tournament.get("tournament_date")
    end_raw = tournament.get("end_date") or start_raw
    if not start_raw:
        return set()
    try:
        start = date.fromisoformat(str(start_raw))
        end = date.fromisoformat(str(end_raw))
    except ValueError as exc:
        raise ValueError("Cupens datum är ogiltigt") from exc
    if end < start:
        raise ValueError("Cupens slutdatum ligger före startdatum")
    result: set[str] = set()
    current = start
    while current <= end:
        result.add(current.isoformat())
        current += timedelta(days=1)
    return result


def _time_text(value, field: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"{field} måste anges som HH:MM") from exc
    return text


def _normalized_rows(payload: dict) -> list[dict]:
    rows = []
    for raw in payload.get("pitch_windows") or []:
        if not isinstance(raw, dict):
            continue
        rows.append({
            "venue": " ".join(str(raw.get("venue") or "").split()) or None,
            "date": str(raw.get("date") or "").strip() or None,
            "start_time": str(raw.get("start_time") or "").strip() or None,
            "end_time": str(raw.get("end_time") or "").strip() or None,
        })
    return rows


def pitch_window_import_review(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    payload = _snapshot(tournament_id)
    rows = _normalized_rows(payload)
    pitches = all_rows(
        "SELECT pitch_number,name FROM pitches WHERE tournament_id=? ORDER BY pitch_number",
        (int(tournament_id),),
    )
    pitch_map = {str(row.get("name") or "").strip().casefold(): int(row["pitch_number"]) for row in pitches}
    persisted = all_rows(
        """SELECT pitch_number,play_date,start_time,end_time,confirmed
           FROM pitch_day_windows WHERE tournament_id=?""",
        (int(tournament_id),),
    )
    current = {
        (int(row["pitch_number"]), str(row["play_date"])): row
        for row in persisted
    }
    pending = []
    already_applied = 0
    for row in rows:
        pitch_number = pitch_map.get(str(row.get("venue") or "").casefold())
        existing = current.get((pitch_number, str(row.get("date")))) if pitch_number is not None else None
        if (
            existing
            and bool(existing.get("confirmed") or 0)
            and str(existing.get("start_time") or "") == str(row.get("start_time") or "")
            and str(existing.get("end_time") or "") == str(row.get("end_time") or "")
        ):
            already_applied += 1
        else:
            pending.append(row)
    return {
        "available": bool(pending),
        "source_name": payload.get("source_name"),
        "pitch_windows": pending,
        "found_count": len(rows),
        "already_applied_count": already_applied,
        "pitches": pitches,
    }


def commit_pitch_window_import(account_id: int, tournament_id: int, pitch_windows: list[dict]):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    rows = [dict(row) for row in (pitch_windows or []) if isinstance(row, dict)]
    if not rows:
        raise ValueError("Det finns inga granskade plantider att importera")
    if len(rows) > 500:
        raise ValueError("Högst 500 plantider kan importeras åt gången")

    tournament = one(
        "SELECT id,start_date,end_date,tournament_date FROM tournaments WHERE id=?",
        (int(tournament_id),),
    ) or {}
    valid_dates = _cup_dates(tournament)
    if not valid_dates:
        raise ValueError("Cupen saknar datum. Ange cupdatum innan plantider importeras")

    pitches = all_rows(
        "SELECT pitch_number,name FROM pitches WHERE tournament_id=? ORDER BY pitch_number",
        (int(tournament_id),),
    )
    pitch_map = {str(row.get("name") or "").strip().casefold(): int(row["pitch_number"]) for row in pitches}
    clean: list[tuple[int, int, str, str, str, int]] = []
    seen: set[tuple[int, str]] = set()
    for index, row in enumerate(rows, start=1):
        venue = " ".join(str(row.get("venue") or "").split())
        if not venue:
            raise ValueError(f"Rad {index}: plan/anläggning saknas")
        pitch_number = pitch_map.get(venue.casefold())
        if pitch_number is None:
            raise ValueError(f"Rad {index}: planen '{venue}' finns inte i cupen. Matcha plannamnet innan import")
        play_date = str(row.get("date") or "").strip()
        if not play_date:
            raise ValueError(f"Rad {index}: datum saknas. CupNavi gissar inte vilken dag plantiden gäller")
        if play_date not in valid_dates:
            raise ValueError(f"Rad {index}: datumet {play_date} ligger utanför cupens datumintervall")
        start_time = _time_text(row.get("start_time"), f"Rad {index} starttid")
        end_time = _time_text(row.get("end_time"), f"Rad {index} sluttid")
        if start_time >= end_time:
            raise ValueError(f"Rad {index}: sluttiden måste vara senare än starttiden")
        key = (pitch_number, play_date)
        if key in seen:
            raise ValueError(f"Rad {index}: samma plan och datum förekommer flera gånger")
        seen.add(key)
        clean.append((int(tournament_id), pitch_number, play_date, start_time, end_time, 1))

    with connect() as con:
        try:
            for values in clean:
                con.execute(
                    """INSERT INTO pitch_day_windows(tournament_id,pitch_number,play_date,start_time,end_time,confirmed)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(tournament_id,pitch_number,play_date) DO UPDATE SET
                         start_time=excluded.start_time,end_time=excluded.end_time,confirmed=1""",
                    values,
                )
            scheduled = con.execute(
                "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
                (int(tournament_id),),
            ).fetchone()
            if scheduled and int(scheduled[0] or 0) > 0:
                con.execute(
                    "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
                    (int(tournament_id),),
                )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        except Exception:
            rollback = getattr(con, "rollback", None)
            if callable(rollback):
                rollback()
            raise
    return {"imported": len(clean), "review": pitch_window_import_review(account_id, tournament_id)}
