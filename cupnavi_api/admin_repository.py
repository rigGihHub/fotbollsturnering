"""Organizer-scoped read/write access for the CupNavi admin API."""
from __future__ import annotations

import hmac

from .admin_auth import OWNER_ACCOUNT_ID, normalize_email, password_hash
from .repository import all_rows, connect, one

CUPINFO_FIELDS = (
    "name",
    "start_date",
    "end_date",
    "organizer",
    "arena_address",
    "organizer_phone",
    "feedback_email",
    "public_information",
)

TEAM_FIELDS = ("name", "age_class", "primary_color", "secondary_color")
TEAM_PROJECTION = "id,tournament_id,name,group_id,age_class,primary_color,secondary_color"


def authenticate_organizer(email: str, password: str):
    normalized_email = normalize_email(email)
    account = one(
        """SELECT id,email,display_name,password_salt,password_hash,disabled_at
           FROM organizer_accounts WHERE email=?""",
        (normalized_email,),
    )
    if not account or account.get("disabled_at"):
        return None
    try:
        candidate = password_hash(password, account["password_salt"])
    except (TypeError, ValueError):
        return None
    if not hmac.compare_digest(candidate, str(account.get("password_hash") or "")):
        return None
    return {
        "id": int(account["id"]),
        "email": normalize_email(account["email"]),
        "display_name": account.get("display_name"),
    }


def organizer_account(account_id: int):
    row = one(
        "SELECT id,email,display_name,disabled_at FROM organizer_accounts WHERE id=?",
        (int(account_id),),
    )
    if not row or row.get("disabled_at"):
        return None
    return {
        "id": int(row["id"]),
        "email": normalize_email(row["email"]),
        "display_name": row.get("display_name"),
    }


def organizer_tournaments(account_id: int):
    if int(account_id) == OWNER_ACCOUNT_ID:
        rows = all_rows(
            """SELECT id,name,public_slug,start_date,end_date,is_published
               FROM tournaments
               ORDER BY COALESCE(start_date,''),name,id"""
        )
        for row in rows:
            row["role"] = "owner"
        return rows
    return all_rows(
        """SELECT t.id,t.name,t.public_slug,t.start_date,t.end_date,t.is_published,tm.role
           FROM tournament_members tm
           JOIN tournaments t ON t.id=tm.tournament_id
           WHERE tm.organizer_account_id=?
           ORDER BY COALESCE(t.start_date,''),t.name,t.id""",
        (int(account_id),),
    )


def _has_tournament_access(account_id: int, tournament_id: int) -> bool:
    if int(account_id) == OWNER_ACCOUNT_ID:
        return bool(one("SELECT 1 AS allowed FROM tournaments WHERE id=?", (int(tournament_id),)))
    return bool(
        one(
            """SELECT 1 AS allowed FROM tournament_members
               WHERE organizer_account_id=? AND tournament_id=?""",
            (int(account_id), int(tournament_id)),
        )
    )


def admin_cupinfo(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    fields = ",".join(("id", "public_slug", "is_published", *CUPINFO_FIELDS))
    return one(f"SELECT {fields} FROM tournaments WHERE id=?", (int(tournament_id),))


def update_cupinfo(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    clean = {}
    for field in CUPINFO_FIELDS:
        if field not in values:
            continue
        value = values[field]
        if value is None:
            clean[field] = None
        else:
            text = str(value).strip()
            clean[field] = text or None
    if "name" in clean and not clean["name"]:
        raise ValueError("Cupnamn krävs")
    if clean:
        assignments = ",".join(f"{field}=?" for field in clean)
        params = [clean[field] for field in clean]
        params.append(int(tournament_id))
        with connect() as con:
            con.execute(f"UPDATE tournaments SET {assignments} WHERE id=?", tuple(params))
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
    return admin_cupinfo(account_id, tournament_id)


def admin_teams(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return all_rows(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )


def _clean_team(values: dict, *, require_name: bool = False) -> dict:
    clean = {}
    for field in TEAM_FIELDS:
        if field not in values:
            continue
        value = values[field]
        text = str(value).strip() if value is not None else ""
        clean[field] = text or None
    if require_name and not clean.get("name"):
        raise ValueError("Lagnamn krävs")
    if "name" in clean and not clean["name"]:
        raise ValueError("Lagnamn krävs")
    for field in ("primary_color", "secondary_color"):
        color = clean.get(field)
        if color is not None and (
            len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:])
        ):
            raise ValueError("Lagfärger måste anges som #RRGGBB")
    return clean


def _team(account_id: int, tournament_id: int, team_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return one(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )


def create_team(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    clean = _clean_team(values, require_name=True)
    clean.setdefault("age_class", None)
    clean.setdefault("primary_color", "#111827")
    clean.setdefault("secondary_color", "#FFFFFF")
    with connect() as con:
        duplicate = con.execute(
            "SELECT id FROM teams WHERE tournament_id=? AND lower(trim(name))=lower(?)",
            (int(tournament_id), clean["name"]),
        ).fetchone()
        if duplicate:
            raise ValueError("Det finns redan ett lag med samma namn")
        cursor = con.execute(
            """INSERT INTO teams(tournament_id,name,age_class,primary_color,secondary_color)
               VALUES(?,?,?,?,?)""",
            (int(tournament_id), clean["name"], clean["age_class"], clean["primary_color"], clean["secondary_color"]),
        )
        team_id = int(cursor.lastrowid)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _team(account_id, tournament_id, team_id)


def update_team(account_id: int, tournament_id: int, team_id: int, values: dict):
    current = _team(account_id, tournament_id, team_id)
    if not current:
        return None
    clean = _clean_team(values)
    if "name" in clean:
        duplicate = one(
            """SELECT id FROM teams WHERE tournament_id=? AND id<>?
               AND lower(trim(name))=lower(?)""",
            (int(tournament_id), int(team_id), clean["name"]),
        )
        if duplicate:
            raise ValueError("Det finns redan ett lag med samma namn")
    if clean:
        assignments = ",".join(f"{field}=?" for field in clean)
        with connect() as con:
            con.execute(
                f"UPDATE teams SET {assignments} WHERE id=? AND tournament_id=?",
                (*[clean[field] for field in clean], int(team_id), int(tournament_id)),
            )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
    return _team(account_id, tournament_id, team_id)


def delete_team(account_id: int, tournament_id: int, team_id: int):
    current = _team(account_id, tournament_id, team_id)
    if not current:
        return None
    token = f"team:{int(team_id)}"
    referenced = one(
        """SELECT id FROM matches WHERE tournament_id=? AND (home_source=? OR away_source=?) LIMIT 1""",
        (int(tournament_id), token, token),
    )
    if referenced:
        raise ValueError("Laget används i schemat och kan inte tas bort förrän matcherna har hanterats")
    with connect() as con:
        con.execute("DELETE FROM teams WHERE id=? AND tournament_id=?", (int(team_id), int(tournament_id)))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current
