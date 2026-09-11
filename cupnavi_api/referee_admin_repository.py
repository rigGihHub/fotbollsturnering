"""Organizer-scoped referee administration using the existing CupNavi schema."""
from __future__ import annotations

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _columns(con, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _referee_columns() -> set[str]:
    with connect() as con:
        return _columns(con, "referees")


def _match_referee_column() -> str | None:
    with connect() as con:
        columns = _columns(con, "matches")
    for candidate in ("referee_id", "assigned_referee_id"):
        if candidate in columns:
            return candidate
    return None


def _projection(columns: set[str]) -> str:
    fields = [field for field in ("id", "tournament_id", "name", "email", "phone", "notes", "active") if field in columns]
    return ",".join(fields)


def admin_referees(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    columns = _referee_columns()
    if not {"id", "tournament_id", "name"}.issubset(columns):
        return {"available": False, "reason": "Domartabellen saknar förväntade kärnfält", "referees": [], "matches": []}
    projection = _projection(columns)
    referees = all_rows(
        f"SELECT {projection} FROM referees WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    referee_by_id = {int(row["id"]): str(row.get("name") or f"Domare {row['id']}") for row in referees}
    match_column = _match_referee_column()
    matches = []
    if match_column:
        matches = all_rows(
            f"""SELECT id,stage,match_no,scheduled_start,pitch_number,{match_column} AS referee_id,
                       home_source,away_source,home_score,away_score
                FROM matches WHERE tournament_id=?
                ORDER BY CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,scheduled_start,id""",
            (int(tournament_id),),
        )
        for match in matches:
            referee_id = match.get("referee_id")
            match["referee_name"] = referee_by_id.get(int(referee_id)) if referee_id is not None else None
            match["played"] = match.get("home_score") is not None and match.get("away_score") is not None
    assignment_counts = {int(row["id"]): 0 for row in referees}
    for match in matches:
        rid = match.get("referee_id")
        if rid is not None and int(rid) in assignment_counts:
            assignment_counts[int(rid)] += 1
    for referee in referees:
        referee["assignment_count"] = assignment_counts.get(int(referee["id"]), 0)
    return {
        "available": True,
        "referees": referees,
        "matches": matches,
        "supports_assignment": bool(match_column),
        "supported_fields": sorted(columns & {"name", "email", "phone", "notes", "active"}),
    }


def _clean_referee(values: dict, columns: set[str], *, require_name: bool = False) -> dict:
    clean = {}
    for field in ("name", "email", "phone", "notes"):
        if field not in columns or field not in values:
            continue
        text = str(values[field] or "").strip()
        clean[field] = text or None
    if "active" in columns and "active" in values:
        clean["active"] = 1 if bool(values["active"]) else 0
    if require_name and not clean.get("name"):
        raise ValueError("Domarnamn krävs")
    if "name" in clean and not clean["name"]:
        raise ValueError("Domarnamn krävs")
    return clean


def create_referee(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    columns = _referee_columns()
    if not {"id", "tournament_id", "name"}.issubset(columns):
        raise ValueError("Domartabellen är inte kompatibel med nya adminen")
    clean = _clean_referee(values, columns, require_name=True)
    insert_fields = ["tournament_id", *clean.keys()]
    params = [int(tournament_id), *[clean[key] for key in clean]]
    placeholders = ",".join("?" for _ in insert_fields)
    with connect() as con:
        cursor = con.execute(
            f"INSERT INTO referees({','.join(insert_fields)}) VALUES({placeholders})",
            tuple(params),
        )
        referee_id = int(cursor.lastrowid)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one(
        f"SELECT {_projection(columns)} FROM referees WHERE id=? AND tournament_id=?",
        (referee_id, int(tournament_id)),
    )


def update_referee(account_id: int, tournament_id: int, referee_id: int, values: dict):
    payload = admin_referees(account_id, tournament_id)
    if payload is None:
        return None
    columns = _referee_columns()
    current = one("SELECT id FROM referees WHERE id=? AND tournament_id=?", (int(referee_id), int(tournament_id)))
    if not current:
        return None
    clean = _clean_referee(values, columns)
    if clean:
        with connect() as con:
            con.execute(
                f"UPDATE referees SET {','.join(f'{key}=?' for key in clean)} WHERE id=? AND tournament_id=?",
                (*[clean[key] for key in clean], int(referee_id), int(tournament_id)),
            )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
    return one(
        f"SELECT {_projection(columns)} FROM referees WHERE id=? AND tournament_id=?",
        (int(referee_id), int(tournament_id)),
    )


def assign_referee(account_id: int, tournament_id: int, match_id: int, referee_id: int | None):
    payload = admin_referees(account_id, tournament_id)
    if payload is None:
        return None
    match_column = _match_referee_column()
    if not match_column:
        raise ValueError("Den befintliga matchtabellen saknar domarkoppling")
    match = one(
        "SELECT id,home_score,away_score FROM matches WHERE id=? AND tournament_id=?",
        (int(match_id), int(tournament_id)),
    )
    if not match:
        return None
    if match.get("home_score") is not None or match.get("away_score") is not None:
        raise ValueError("Domare kan inte bytas på en färdigspelad match här")
    normalized = None if referee_id is None else int(referee_id)
    if normalized is not None:
        referee = one("SELECT id FROM referees WHERE id=? AND tournament_id=?", (normalized, int(tournament_id)))
        if not referee:
            raise ValueError("Domaren finns inte i den aktiva cupen")
    with connect() as con:
        con.execute(
            f"UPDATE matches SET {match_column}=? WHERE id=? AND tournament_id=?",
            (normalized, int(match_id), int(tournament_id)),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_referees(account_id, tournament_id)


def delete_referee(account_id: int, tournament_id: int, referee_id: int):
    payload = admin_referees(account_id, tournament_id)
    if payload is None:
        return None
    current = one("SELECT id,name FROM referees WHERE id=? AND tournament_id=?", (int(referee_id), int(tournament_id)))
    if not current:
        return None
    match_column = _match_referee_column()
    if match_column:
        used = one(
            f"SELECT id FROM matches WHERE tournament_id=? AND {match_column}=? LIMIT 1",
            (int(tournament_id), int(referee_id)),
        )
        if used:
            raise ValueError("Domaren är tilldelad matcher. Flytta uppdragen innan domaren tas bort")
    with connect() as con:
        ack_columns = _columns(con, "referee_acknowledgements")
        if "referee_id" in ack_columns:
            acknowledged = con.execute(
                "SELECT id FROM referee_acknowledgements WHERE tournament_id=? AND referee_id=? LIMIT 1",
                (int(tournament_id), int(referee_id)),
            ).fetchone()
            if acknowledged:
                raise ValueError("Domaren har kvitterad matchhistorik och kan inte tas bort")
        con.execute("DELETE FROM referees WHERE id=? AND tournament_id=?", (int(referee_id), int(tournament_id)))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current
