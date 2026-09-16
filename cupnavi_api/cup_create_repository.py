"""Authenticated organizer creation of new CupNavi cups."""
from __future__ import annotations

import re
import unicodedata

from .admin_auth import OWNER_ACCOUNT_ID
from .repository import connect, one


def _slug_base(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return slug or "cup"


def _unique_slug(name: str) -> str:
    base = _slug_base(name)
    slug = base
    suffix = 2
    while one("SELECT id FROM tournaments WHERE public_slug=?", (slug,)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_owner_tournament(account_id: int, values: dict):
    account_id = int(account_id)
    name = str(values.get("name") or "").strip()
    if not name:
        raise ValueError("Cupnamn krävs")
    if len(name) > 120:
        raise ValueError("Cupnamnet är för långt")

    start_date = str(values.get("start_date") or "").strip() or None
    end_date = str(values.get("end_date") or "").strip() or None
    if start_date and end_date and end_date < start_date:
        raise ValueError("Slutdatum kan inte vara före startdatum")

    slug = _unique_slug(name)
    with connect() as con:
        actor_email = "CupNavi Owner"
        if account_id != OWNER_ACCOUNT_ID:
            actor_row = con.execute("SELECT email FROM organizer_accounts WHERE id=?", (account_id,)).fetchone()
            if not actor_row:
                raise PermissionError("Arrangörskontot finns inte")
            actor_email = str(actor_row[0])
        cursor = con.execute(
            """INSERT INTO tournaments(name,public_slug,start_date,end_date,is_published,lifecycle_status)
               VALUES(?,?,?,?,0,'draft')""",
            (name, slug, start_date, end_date),
        )
        cup_id = int(cursor.lastrowid)
        if account_id != OWNER_ACCOUNT_ID:
            con.execute(
                """INSERT INTO tournament_members(tournament_id,organizer_account_id,role)
                   VALUES(?,?,'owner')""",
                (cup_id, account_id),
            )
        con.execute(
            """INSERT INTO admin_activity(
                   tournament_id,organizer_account_id,actor_email,action,entity_type,entity_id,summary
               ) VALUES(?,?,?,'created','tournament',?,?)""",
            (cup_id, None if account_id == OWNER_ACCOUNT_ID else account_id, actor_email, cup_id, "Cupen skapades"),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()

    cup = one(
        """SELECT id,name,public_slug,start_date,end_date,is_published
           FROM tournaments WHERE id=?""",
        (cup_id,),
    )
    if cup:
        cup["role"] = "owner"
    return cup
