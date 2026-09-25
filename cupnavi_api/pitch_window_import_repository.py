"""Review-first import of pitch opening windows extracted from cup documents."""
from __future__ import annotations

from cupnavi_core.pitch_availability import expand_pitch_windows, validate_intervals, write_pitch_intervals

import json
from collections import Counter
from datetime import date, datetime, timedelta

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one, _dict_rows


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
        parsed = datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"{field} måste anges som HH:MM") from exc
    return parsed.strftime("%H:%M")


def _review_time(value):
    text = str(value or "").strip()
    try:
        return _time_text(text, "Tid")
    except ValueError:
        return text or None


def _single_cup_date(tournament: dict) -> str | None:
    start_raw = tournament.get("start_date") or tournament.get("tournament_date")
    end_raw = tournament.get("end_date") or start_raw
    if not start_raw:
        return None
    try:
        start = date.fromisoformat(str(start_raw))
        end = date.fromisoformat(str(end_raw))
    except ValueError:
        return None
    return start.isoformat() if start == end else None


def _normalized_rows(payload: dict, default_date: str | None = None) -> list[dict]:
    rows = []
    for raw in payload.get("pitch_windows") or []:
        if not isinstance(raw, dict):
            continue
        rows.append({
            "venue": " ".join(str(raw.get("venue") or "").split()) or None,
            # A one-day cup has only one possible date. Persisting it here
            # prevents the review dialog from asking for the same date again.
            "date": str(raw.get("date") or "").strip() or default_date,
            "start_time": _review_time(raw.get("start_time")),
            "end_time": _review_time(raw.get("end_time")),
        })
    return rows


def pitch_window_import_review(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    payload = _snapshot(tournament_id)
    tournament = one(
        "SELECT start_date,end_date,tournament_date FROM tournaments WHERE id=?",
        (int(tournament_id),),
    ) or {}
    rows = _normalized_rows(payload, _single_cup_date(tournament))
    pitches = all_rows(
        "SELECT pitch_number,name FROM pitches WHERE tournament_id=? ORDER BY pitch_number",
        (int(tournament_id),),
    )
    pitch_map = {str(row.get("name") or "").strip().casefold(): int(row["pitch_number"]) for row in pitches}
    persisted = all_rows(
        """SELECT *
           FROM pitch_day_windows WHERE tournament_id=?""",
        (int(tournament_id),),
    )
    persisted = expand_pitch_windows(persisted)
    current = {
        (int(row["pitch_number"]), str(row["play_date"]), str(row["start_time"]), str(row["end_time"])): row
        for row in persisted
    }
    # A reviewed import may map a source venue name (for example an arena) to a
    # renamed CupNavi pitch (for example "Plan 1"). Remember confirmed values as
    # a multiset so that this legitimate mapping does not re-open forever.
    confirmed_values = Counter(
        (
            str(row.get("play_date") or ""),
            str(row.get("start_time") or ""),
            str(row.get("end_time") or ""),
        )
        for row in persisted
        if bool(row.get("confirmed") or 0)
    )
    confirmed_days = {
        (int(row["pitch_number"]), str(row.get("play_date") or ""))
        for row in persisted
        if bool(row.get("confirmed") or 0)
    }
    pending = []
    already_applied = 0
    for row in rows:
        pitch_number = pitch_map.get(str(row.get("venue") or "").casefold())
        existing = current.get((pitch_number, str(row.get("date")), str(row.get("start_time")), str(row.get("end_time")))) if pitch_number is not None else None
        exact_match = (
            existing
            and bool(existing.get("confirmed") or 0)
            and str(existing.get("start_time") or "") == str(row.get("start_time") or "")
            and str(existing.get("end_time") or "") == str(row.get("end_time") or "")
        )
        value_key = (
            str(row.get("date") or ""),
            str(row.get("start_time") or ""),
            str(row.get("end_time") or ""),
        )
        day_reviewed = pitch_number is not None and (pitch_number, str(row.get("date") or "")) in confirmed_days
        if day_reviewed or exact_match:
            # Confirmation is stored for the complete pitch day. The admin may
            # deliberately adjust an imported time before confirming it; the
            # old source value must not then return as unfinished work.
            already_applied += 1
            if confirmed_values[value_key] > 0:
                confirmed_values[value_key] -= 1
        elif confirmed_values[value_key] > 0:
            # The values were confirmed against another/renamed pitch. Consume
            # only one occurrence so equal times on multiple pitches stay safe.
            confirmed_values[value_key] -= 1
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
    grouped = {}
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
        grouped.setdefault(key, []).append({"start_time": start_time, "end_time": end_time})
        clean.append((int(tournament_id), pitch_number, play_date, start_time, end_time, 1))

    with connect() as con:
        try:
            changed = False
            con.execute("BEGIN IMMEDIATE")
            for (pitch_number, play_date), intervals in grouped.items():
                existing = expand_pitch_windows(_dict_rows(con.execute("SELECT * FROM pitch_day_windows WHERE tournament_id=? AND pitch_number=? AND play_date=? AND confirmed=1", (int(tournament_id), pitch_number, play_date))))
                # A resumed/partial review must retain already confirmed passes.
                reviewed = validate_intervals(intervals)
                for old in existing:
                    interval = {"start_time": old["start_time"], "end_time": old["end_time"]}
                    if interval not in reviewed:
                        reviewed.append(interval)
                # write_pitch_intervals persists this through the
                # ON CONFLICT(tournament_id,pitch_number,play_date) upsert.
                changed = write_pitch_intervals(con, tournament_id, pitch_number, play_date, reviewed) or changed
            scheduled = con.execute(
                "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
                (int(tournament_id),),
            ).fetchone()
            if changed and scheduled and int(scheduled[0] or 0) > 0:
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
    return {"imported": len(clean), "changed": changed, "review": pitch_window_import_review(account_id, tournament_id)}
