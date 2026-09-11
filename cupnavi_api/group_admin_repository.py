"""Organizer-scoped group administration for CupNavi."""
from __future__ import annotations

from .admin_repository import _has_tournament_access, _team
from .repository import all_rows, connect, one

GROUP_FIELDS = ("name", "age_class")
GROUP_PROJECTION = "id,tournament_id,name,age_class"


def admin_groups(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    groups = all_rows(
        f"SELECT {GROUP_PROJECTION} FROM groups WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    counts = all_rows(
        """SELECT group_id,COUNT(*) AS team_count FROM teams
           WHERE tournament_id=? AND group_id IS NOT NULL GROUP BY group_id""",
        (int(tournament_id),),
    )
    by_group = {int(row["group_id"]): int(row["team_count"]) for row in counts}
    for group in groups:
        group["team_count"] = by_group.get(int(group["id"]), 0)
    return groups


def _clean_group(values: dict, *, require_name: bool = False) -> dict:
    clean = {}
    for field in GROUP_FIELDS:
        if field not in values:
            continue
        value = values[field]
        text = str(value).strip() if value is not None else ""
        clean[field] = text or None
    if require_name and not clean.get("name"):
        raise ValueError("Gruppnamn krävs")
    if "name" in clean and not clean["name"]:
        raise ValueError("Gruppnamn krävs")
    return clean


def _group(account_id: int, tournament_id: int, group_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    row = one(
        f"SELECT {GROUP_PROJECTION} FROM groups WHERE id=? AND tournament_id=?",
        (int(group_id), int(tournament_id)),
    )
    if row:
        count = one(
            "SELECT COUNT(*) AS team_count FROM teams WHERE tournament_id=? AND group_id=?",
            (int(tournament_id), int(group_id)),
        )
        row["team_count"] = int((count or {}).get("team_count") or 0)
    return row


def create_group(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    clean = _clean_group(values, require_name=True)
    clean.setdefault("age_class", None)
    with connect() as con:
        duplicate = con.execute(
            "SELECT id FROM groups WHERE tournament_id=? AND lower(trim(name))=lower(?)",
            (int(tournament_id), clean["name"]),
        ).fetchone()
        if duplicate:
            raise ValueError("Det finns redan en grupp med samma namn")
        cursor = con.execute(
            "INSERT INTO groups(tournament_id,name,age_class) VALUES(?,?,?)",
            (int(tournament_id), clean["name"], clean["age_class"]),
        )
        group_id = int(cursor.lastrowid)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _group(account_id, tournament_id, group_id)


def update_group(account_id: int, tournament_id: int, group_id: int, values: dict):
    current = _group(account_id, tournament_id, group_id)
    if not current:
        return None
    clean = _clean_group(values)
    if "name" in clean:
        duplicate = one(
            """SELECT id FROM groups WHERE tournament_id=? AND id<>?
               AND lower(trim(name))=lower(?)""",
            (int(tournament_id), int(group_id), clean["name"]),
        )
        if duplicate:
            raise ValueError("Det finns redan en grupp med samma namn")
    if clean:
        assignments = ",".join(f"{field}=?" for field in clean)
        with connect() as con:
            con.execute(
                f"UPDATE groups SET {assignments} WHERE id=? AND tournament_id=?",
                (*[clean[field] for field in clean], int(group_id), int(tournament_id)),
            )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
    return _group(account_id, tournament_id, group_id)


def assign_team_group(account_id: int, tournament_id: int, team_id: int, group_id: int | None):
    team = _team(account_id, tournament_id, team_id)
    if not team:
        return None
    normalized_group_id = None if group_id is None else int(group_id)
    if normalized_group_id is not None and not _group(account_id, tournament_id, normalized_group_id):
        raise ValueError("Gruppen finns inte i den aktiva cupen")
    with connect() as con:
        con.execute(
            "UPDATE teams SET group_id=? WHERE id=? AND tournament_id=?",
            (normalized_group_id, int(team_id), int(tournament_id)),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _team(account_id, tournament_id, team_id)


def delete_group(account_id: int, tournament_id: int, group_id: int):
    current = _group(account_id, tournament_id, group_id)
    if not current:
        return None
    if int(current.get("team_count") or 0) > 0:
        raise ValueError("Gruppen innehåller lag. Flytta eller avgruppera lagen innan gruppen tas bort")
    referenced = one(
        "SELECT id FROM matches WHERE tournament_id=? AND group_id=? LIMIT 1",
        (int(tournament_id), int(group_id)),
    )
    if referenced:
        raise ValueError("Gruppen används i schemat och kan inte tas bort förrän matcherna har hanterats")
    with connect() as con:
        con.execute("DELETE FROM groups WHERE id=? AND tournament_id=?", (int(group_id), int(tournament_id)))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current
