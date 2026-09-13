"""Organizer-scoped read/write access for the CupNavi admin API."""
from __future__ import annotations

import hmac

from .admin_auth import (
    OWNER_ACCOUNT_ID,
    authenticate_owner,
    normalize_email,
    owner_identity,
    password_hash,
)
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
HIDDEN_LIFECYCLE_STATUSES = ("trashed", "purged")


def _table_columns(table_name: str) -> set[str]:
    """Return available SQLite/libSQL columns without assuming the latest migration.

    Older CupNavi databases and focused repository tests can legitimately predate
    the tournament lifecycle columns. Access checks must remain compatible with
    those schemas while the lifecycle migration is rolling out.
    """
    rows = all_rows(f"PRAGMA table_info({table_name})")
    return {str(row.get("name")) for row in rows if row.get("name")}


def authenticate_organizer(email: str, password: str):
    owner = authenticate_owner(email, password)
    if owner:
        return owner
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
    if int(account_id) == OWNER_ACCOUNT_ID:
        return owner_identity()
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
               WHERE COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')
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
             AND COALESCE(t.lifecycle_status,'draft') NOT IN ('trashed','purged')
           ORDER BY COALESCE(t.start_date,''),t.name,t.id""",
        (int(account_id),),
    )


def trashed_tournaments(account_id: int):
    """Return recoverable cups for the app owner only."""
    if int(account_id) != OWNER_ACCOUNT_ID:
        raise PermissionError("Endast CupNavi-ägaren kan visa papperskorgen")
    rows = all_rows(
        """SELECT id,name,public_slug,start_date,end_date,is_published,trashed_at
           FROM tournaments
           WHERE COALESCE(lifecycle_status,'draft')='trashed'
           ORDER BY COALESCE(trashed_at,'' ) DESC,name,id"""
    )
    for row in rows:
        row["role"] = "owner"
    return rows


def purge_trashed_tournaments(account_id: int) -> int:
    """Empty the visible trash for the app owner.

    Purged cups are kept as hidden tombstones instead of deleting relational data.
    They are no longer listed, restorable, accessible in admin or published.
    """
    if int(account_id) != OWNER_ACCOUNT_ID:
        raise PermissionError("Endast CupNavi-ägaren kan tömma papperskorgen")
    with connect() as con:
        cursor = con.execute(
            """UPDATE tournaments
               SET lifecycle_status='purged',trashed_at=NULL,is_published=0
               WHERE COALESCE(lifecycle_status,'draft')='trashed'"""
        )
        count = getattr(cursor, "rowcount", None)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return max(0, int(count)) if count is not None and int(count) >= 0 else 0


def _has_tournament_access(account_id: int, tournament_id: int) -> bool:
    account_id = int(account_id)
    tournament_id = int(tournament_id)
    tournament_columns = _table_columns("tournaments")

    if account_id == OWNER_ACCOUNT_ID:
        if not tournament_columns:
            return False
        if "lifecycle_status" not in tournament_columns:
            return bool(one("SELECT 1 AS allowed FROM tournaments WHERE id=?", (tournament_id,)))
        return bool(one(
            """SELECT 1 AS allowed FROM tournaments
               WHERE id=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')""",
            (tournament_id,),
        ))

    member = one(
        """SELECT 1 AS allowed FROM tournament_members
           WHERE organizer_account_id=? AND tournament_id=?""",
        (account_id, tournament_id),
    )
    if not member:
        return False

    # Legacy/focused schemas may have membership data without a tournaments table,
    # or may predate lifecycle_status. Membership remains the authoritative check
    # until that migration exists; once it does, trashed/purged cups are blocked.
    if not tournament_columns or "lifecycle_status" not in tournament_columns:
        return True
    return bool(one(
        """SELECT 1 AS allowed FROM tournaments
           WHERE id=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')""",
        (tournament_id,),
    ))


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
            clean[field] = str(value).strip()
    if not clean:
        return admin_cupinfo(account_id, tournament_id)
    assignments = ",".join(f"{field}=?" for field in clean)
    params = tuple(clean[field] for field in clean) + (int(tournament_id),)
    with connect() as con:
        con.execute(f"UPDATE tournaments SET {assignments} WHERE id=?", params)
        con.execute("UPDATE tournaments SET is_published=0 WHERE id=?", (int(tournament_id),))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_cupinfo(account_id, tournament_id)


def admin_teams(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return []
    return all_rows(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )


def create_team(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    name = str(values.get("name") or "").strip()
    if not name:
        raise ValueError("Lagnamn krävs")
    clean = {
        "name": name,
        "age_class": str(values.get("age_class") or "").strip() or None,
        "primary_color": str(values.get("primary_color") or "").strip() or None,
        "secondary_color": str(values.get("secondary_color") or "").strip() or None,
    }
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO teams(tournament_id,name,age_class,primary_color,secondary_color)
               VALUES(?,?,?,?,?)""",
            (
                int(tournament_id),
                clean["name"],
                clean["age_class"],
                clean["primary_color"],
                clean["secondary_color"],
            ),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
        team_id = int(cursor.lastrowid)
    return one(f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=?", (team_id,))


def update_team(account_id: int, tournament_id: int, team_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    current = one(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )
    if not current:
        return None
    clean = {}
    for field in TEAM_FIELDS:
        if field not in values:
            continue
        value = str(values[field] or "").strip()
        if field == "name" and not value:
            raise ValueError("Lagnamn krävs")
        clean[field] = value or None
    if not clean:
        return current
    assignments = ",".join(f"{field}=?" for field in clean)
    params = tuple(clean[field] for field in clean) + (int(team_id), int(tournament_id))
    with connect() as con:
        con.execute(f"UPDATE teams SET {assignments} WHERE id=? AND tournament_id=?", params)
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )


def delete_team(account_id: int, tournament_id: int, team_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    current = one(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )
    if not current:
        return None
    with connect() as con:
        con.execute("DELETE FROM teams WHERE id=? AND tournament_id=?", (int(team_id), int(tournament_id)))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current
