"""Organizer-scoped pitch and availability administration for CupNavi."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _time_text(value, field: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"{field} måste anges som HH:MM") from exc
    return text


def _tournament(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return one(
        "SELECT id,start_date,end_date,tournament_date,schedule_dirty FROM tournaments WHERE id=?",
        (int(tournament_id),),
    )


def _schedule_rules(tournament_id: int):
    rules = one("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))
    if rules:
        return rules
    with connect() as con:
        con.execute("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (int(tournament_id),))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))


def _cup_dates(tournament: dict) -> list[str]:
    start_raw = tournament.get("start_date") or tournament.get("tournament_date")
    end_raw = tournament.get("end_date") or start_raw
    if not start_raw:
        return []
    start = date.fromisoformat(str(start_raw))
    end = date.fromisoformat(str(end_raw))
    if end < start:
        raise ValueError("Cupens slutdatum ligger före startdatum")
    result = []
    current = start
    while current <= end:
        result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def _mark_schedule_dirty(con, tournament_id: int):
    scheduled = con.execute(
        "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (int(tournament_id),),
    ).fetchone()
    count = int(scheduled[0] or 0) if scheduled else 0
    if count:
        con.execute("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (int(tournament_id),))
    return count


def _ensure_pitch_rows(con, tournament_id: int, pitch_count: int):
    existing = {
        int(row[0]) for row in con.execute(
            "SELECT pitch_number FROM pitches WHERE tournament_id=?",
            (int(tournament_id),),
        ).fetchall()
    }
    for pitch_number in range(1, int(pitch_count) + 1):
        if pitch_number not in existing:
            con.execute(
                "INSERT INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)",
                (int(tournament_id), pitch_number, f"Plan {pitch_number}"),
            )


def _ensure_pitch_windows(con, tournament_id: int, pitch_count: int, dates: list[str], start_time: str, end_time: str):
    for play_date in dates:
        for pitch_number in range(1, int(pitch_count) + 1):
            con.execute(
                """INSERT OR IGNORE INTO pitch_day_windows(
                       tournament_id,pitch_number,play_date,start_time,end_time,confirmed
                   ) VALUES(?,?,?,?,?,0)""",
                (int(tournament_id), pitch_number, play_date, start_time, end_time),
            )


def admin_venues(account_id: int, tournament_id: int):
    tournament = _tournament(account_id, tournament_id)
    if not tournament:
        return None
    rules = _schedule_rules(tournament_id) or {}
    pitch_count = max(1, int(rules.get("pitch_count") or 1))
    first_time = str(rules.get("first_match_time") or "09:00")
    latest_time = str(rules.get("latest_kickoff_time") or "18:00")
    dates = _cup_dates(tournament)
    with connect() as con:
        _ensure_pitch_rows(con, tournament_id, pitch_count)
        _ensure_pitch_windows(con, tournament_id, pitch_count, dates, first_time, latest_time)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    pitches = all_rows(
        """SELECT tournament_id,pitch_number,name,address,address_verified
           FROM pitches WHERE tournament_id=? AND pitch_number<=? ORDER BY pitch_number""",
        (int(tournament_id), pitch_count),
    )
    windows = all_rows(
        """SELECT tournament_id,pitch_number,play_date,start_time,end_time,confirmed
           FROM pitch_day_windows WHERE tournament_id=? AND pitch_number<=?
           ORDER BY play_date,pitch_number""",
        (int(tournament_id), pitch_count),
    )
    schedule_state = one(
        """SELECT COUNT(*) AS scheduled_count,COALESCE(MAX(pitch_number),0) AS max_used_pitch
           FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL""",
        (int(tournament_id),),
    ) or {}
    return {
        "rules": {
            "pitch_count": pitch_count,
            "first_match_time": first_time,
            "latest_kickoff_time": latest_time,
            "synchronized_pitch_times": bool(rules.get("synchronized_pitch_times") or 0),
            "consider_pitch_travel": bool(rules.get("consider_pitch_travel") or 0),
        },
        "dates": dates,
        "pitches": pitches,
        "windows": windows,
        "scheduled_count": int(schedule_state.get("scheduled_count") or 0),
        "max_used_pitch": int(schedule_state.get("max_used_pitch") or 0),
        "schedule_dirty": bool(tournament.get("schedule_dirty") or 0),
    }


def update_venue_rules(account_id: int, tournament_id: int, values: dict):
    tournament = _tournament(account_id, tournament_id)
    if not tournament:
        return None
    rules = _schedule_rules(tournament_id) or {}
    pitch_count = int(values.get("pitch_count", rules.get("pitch_count") or 1))
    if pitch_count < 1 or pitch_count > 50:
        raise ValueError("Antal planer måste vara mellan 1 och 50")
    first_time = _time_text(values.get("first_match_time", rules.get("first_match_time") or "09:00"), "Första avspark")
    latest_time = _time_text(values.get("latest_kickoff_time", rules.get("latest_kickoff_time") or "18:00"), "Sista avspark")
    if first_time >= latest_time:
        raise ValueError("Sista avspark måste vara senare än första avspark")
    synchronized = 1 if bool(values.get("synchronized_pitch_times", rules.get("synchronized_pitch_times") or 0)) else 0
    consider_travel = 1 if bool(values.get("consider_pitch_travel", rules.get("consider_pitch_travel") or 0)) else 0
    dates = _cup_dates(tournament)
    with connect() as con:
        used = con.execute(
            """SELECT COALESCE(MAX(pitch_number),0) FROM matches
               WHERE tournament_id=? AND scheduled_start IS NOT NULL""",
            (int(tournament_id),),
        ).fetchone()
        max_used = int(used[0] or 0) if used else 0
        if max_used > pitch_count:
            raise ValueError(
                f"Schemat använder redan plan {max_used}. Flytta de matcherna innan antalet planer minskas till {pitch_count}"
            )
        con.execute(
            """UPDATE schedule_rules SET pitch_count=?,first_match_time=?,latest_kickoff_time=?,
                   synchronized_pitch_times=?,consider_pitch_travel=? WHERE tournament_id=?""",
            (pitch_count, first_time, latest_time, synchronized, consider_travel, int(tournament_id)),
        )
        con.execute(
            """UPDATE pitch_day_windows SET start_time=?,end_time=?
               WHERE tournament_id=? AND confirmed=0""",
            (first_time, latest_time, int(tournament_id)),
        )
        _ensure_pitch_rows(con, tournament_id, pitch_count)
        _ensure_pitch_windows(con, tournament_id, pitch_count, dates, first_time, latest_time)
        _mark_schedule_dirty(con, tournament_id)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_venues(account_id, tournament_id)


def update_pitch(account_id: int, tournament_id: int, pitch_number: int, values: dict):
    tournament = _tournament(account_id, tournament_id)
    if not tournament:
        return None
    rules = _schedule_rules(tournament_id) or {}
    pitch_count = max(1, int(rules.get("pitch_count") or 1))
    pitch_number = int(pitch_number)
    if pitch_number < 1 or pitch_number > pitch_count:
        raise ValueError("Planen ligger utanför cupens aktuella plankapacitet")
    current = one(
        "SELECT name,address FROM pitches WHERE tournament_id=? AND pitch_number=?",
        (int(tournament_id), pitch_number),
    ) or {}
    name = str(values.get("name", current.get("name") or f"Plan {pitch_number}") or "").strip()
    address = str(values.get("address", current.get("address") or "") or "").strip() or None
    if not name:
        raise ValueError("Plannamn krävs")
    with connect() as con:
        con.execute(
            """INSERT INTO pitches(tournament_id,pitch_number,name,address,address_verified)
               VALUES(?,?,?,?,0)
               ON CONFLICT(tournament_id,pitch_number) DO UPDATE SET
                 name=excluded.name,address=excluded.address,
                 address_verified=CASE WHEN COALESCE(pitches.address,'')=COALESCE(excluded.address,'') THEN pitches.address_verified ELSE 0 END""",
            (int(tournament_id), pitch_number, name, address),
        )
        _mark_schedule_dirty(con, tournament_id)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_venues(account_id, tournament_id)


def update_pitch_window(account_id: int, tournament_id: int, pitch_number: int, play_date: str, values: dict):
    tournament = _tournament(account_id, tournament_id)
    if not tournament:
        return None
    rules = _schedule_rules(tournament_id) or {}
    pitch_count = max(1, int(rules.get("pitch_count") or 1))
    pitch_number = int(pitch_number)
    if pitch_number < 1 or pitch_number > pitch_count:
        raise ValueError("Planen ligger utanför cupens aktuella plankapacitet")
    play_date = str(play_date).strip()
    if play_date not in _cup_dates(tournament):
        raise ValueError("Datumet ligger utanför cupens datumintervall")
    start_time = _time_text(values.get("start_time"), "Starttid")
    end_time = _time_text(values.get("end_time"), "Sluttid")
    if start_time >= end_time:
        raise ValueError("Sluttiden måste vara senare än starttiden")
    confirmed = 1 if bool(values.get("confirmed", True)) else 0
    with connect() as con:
        con.execute(
            """INSERT INTO pitch_day_windows(tournament_id,pitch_number,play_date,start_time,end_time,confirmed)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(tournament_id,pitch_number,play_date) DO UPDATE SET
                 start_time=excluded.start_time,end_time=excluded.end_time,confirmed=excluded.confirmed""",
            (int(tournament_id), pitch_number, play_date, start_time, end_time, confirmed),
        )
        _mark_schedule_dirty(con, tournament_id)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_venues(account_id, tournament_id)
