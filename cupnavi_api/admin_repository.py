"""Organizer-scoped read/write access for the CupNavi admin API."""
from __future__ import annotations

import hmac

from .admin_auth import normalize_email, password_hash
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


def authenticate_organizer(email: str, password: str):
    account = one(
        """SELECT id,email,display_name,password_salt,password_hash,disabled_at
           FROM organizer_accounts WHERE email=?""",
        (normalize_email(email),),
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
    return all_rows(
        """SELECT t.id,t.name,t.public_slug,t.start_date,t.end_date,t.is_published,tm.role
           FROM tournament_members tm
           JOIN tournaments t ON t.id=tm.tournament_id
           WHERE tm.organizer_account_id=?
           ORDER BY COALESCE(t.start_date,''),t.name,t.id""",
        (int(account_id),),
    )


def _has_tournament_access(account_id: int, tournament_id: int) -> bool:
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
