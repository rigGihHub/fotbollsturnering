"""Organizer-scoped schedule administration for the new CupNavi admin."""
from __future__ import annotations

from datetime import datetime

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one
from .schedule_conflicts import analyze_schedule_conflicts


def _team_names(tournament_id: int) -> dict[int, str]:
    rows = all_rows(
        "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    return {int(row["id"]): str(row["name"]) for row in rows}


def _source_label(source, team_names: dict[int, str]) -> str:
    text = str(source or "").strip()
    if text.startswith("team:"):
        try:
            team_id = int(text.split(":", 1)[1])
        except (TypeError, ValueError):
            return text or "Ej satt"
        return team_names.get(team_id, f"Lag {team_id}")
    return text or "Ej satt"


def admin_schedule(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one(
        "SELECT id,start_date,end_date,schedule_dirty,is_published FROM tournaments WHERE id=?",
        (int(tournament_id),),
    )
    if not tournament:
        return None
    rules = one(
        """SELECT pitch_count,first_match_time,latest_kickoff_time,
                  halves,minutes_per_half,halftime_minutes,pitch_break_minutes,
                  minimum_team_rest_minutes
           FROM schedule_rules WHERE tournament_id=?""",
        (int(tournament_id),),
    ) or {
        "pitch_count": 1,
        "first_match_time": "09:00",
        "latest_kickoff_time": "18:00",
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 0,
    }
    groups = all_rows(
        "SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    group_names = {int(row["id"]): str(row["name"]) for row in groups}
    team_names = _team_names(tournament_id)
    rows = all_rows(
        """SELECT id,group_id,bracket_id,stage,match_no,round_no,home_source,away_source,
                  scheduled_start,pitch_number,schedule_locked,schedule_published,
                  home_score,away_score
           FROM matches WHERE tournament_id=?
           ORDER BY CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,scheduled_start,
                    stage,group_id,round_no,match_no,id""",
        (int(tournament_id),),
    )
    for row in rows:
        row["home_label"] = _source_label(row.get("home_source"), team_names)
        row["away_label"] = _source_label(row.get("away_source"), team_names)
        row["group_name"] = group_names.get(int(row["group_id"])) if row.get("group_id") is not None else None
        row["played"] = row.get("home_score") is not None and row.get("away_score") is not None
        row["schedule_locked"] = bool(row.get("schedule_locked") or 0)
        row["schedule_published"] = bool(row.get("schedule_published") or 0)
    scheduled_count = sum(1 for row in rows if row.get("scheduled_start"))
    conflict_analysis = analyze_schedule_conflicts(rows, rules)
    return {
        "matches": rows,
        "match_count": len(rows),
        "scheduled_count": scheduled_count,
        "unscheduled_count": len(rows) - scheduled_count,
        "pitch_count": max(1, int(rules.get("pitch_count") or 1)),
        "first_match_time": str(rules.get("first_match_time") or "09:00"),
        "latest_kickoff_time": str(rules.get("latest_kickoff_time") or "18:00"),
        "start_date": tournament.get("start_date"),
        "end_date": tournament.get("end_date"),
        "schedule_dirty": bool(tournament.get("schedule_dirty") or 0),
        "is_published": bool(tournament.get("is_published") or 0),
        "conflict_analysis": conflict_analysis,
    }


def update_match_schedule(account_id: int, tournament_id: int, match_id: int, values: dict):
    payload = admin_schedule(account_id, tournament_id)
    if payload is None:
        return None
    current = one(
        """SELECT id,scheduled_start,pitch_number,schedule_locked,home_score,away_score
           FROM matches WHERE id=? AND tournament_id=?""",
        (int(match_id), int(tournament_id)),
    )
    if not current:
        return None
    if current.get("home_score") is not None or current.get("away_score") is not None:
        raise ValueError("En färdigspelad matchs tid eller plan kan inte ändras här")
    if bool(current.get("schedule_locked") or 0):
        raise ValueError("Matchen är låst. Lås upp den i det avancerade schemaflödet innan tiden ändras")

    raw_start = values.get("scheduled_start", current.get("scheduled_start"))
    raw_pitch = values.get("pitch_number", current.get("pitch_number"))
    scheduled_start = None
    if raw_start not in (None, ""):
        text = str(raw_start).strip()
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("Matchtiden måste vara ett giltigt datum och klockslag") from exc
        start_date = payload.get("start_date")
        end_date = payload.get("end_date") or start_date
        if start_date and parsed.date().isoformat() < str(start_date):
            raise ValueError("Matchtiden ligger före cupens första dag")
        if end_date and parsed.date().isoformat() > str(end_date):
            raise ValueError("Matchtiden ligger efter cupens sista dag")
        scheduled_start = parsed.isoformat(timespec="minutes")

    pitch_number = None
    if raw_pitch not in (None, ""):
        try:
            pitch_number = int(raw_pitch)
        except (TypeError, ValueError) as exc:
            raise ValueError("Plan måste vara ett heltal") from exc
        if pitch_number < 1 or pitch_number > int(payload["pitch_count"]):
            raise ValueError(f"Plan måste vara mellan 1 och {payload['pitch_count']}")
    if (scheduled_start is None) != (pitch_number is None):
        raise ValueError("Tid och plan måste antingen anges tillsammans eller båda tas bort")

    with connect() as con:
        con.execute(
            """UPDATE matches SET scheduled_start=?,pitch_number=?,schedule_published=0
               WHERE id=? AND tournament_id=?""",
            (scheduled_start, pitch_number, int(match_id), int(tournament_id)),
        )
        con.execute(
            "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
            (int(tournament_id),),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_schedule(account_id, tournament_id)
