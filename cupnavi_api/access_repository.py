"""Tournament membership, role and administrator activity management."""
from __future__ import annotations

import hmac
import os
import secrets

from .admin_auth import OWNER_ACCOUNT_ID, normalize_email, password_hash
from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one

MEMBER_ROLES = {"owner", "admin"}


def tournament_role(account_id: int, tournament_id: int) -> str | None:
    if int(account_id) == OWNER_ACCOUNT_ID:
        return "platform_owner" if _has_tournament_access(account_id, tournament_id) else None
    row = one(
        "SELECT role FROM tournament_members WHERE tournament_id=? AND organizer_account_id=?",
        (int(tournament_id), int(account_id)),
    )
    return str(row["role"]) if row else None


def _can_manage_members(account_id: int, tournament_id: int) -> bool:
    return tournament_role(account_id, tournament_id) in {"platform_owner", "owner"}


def _record_activity(con, tournament_id: int, actor: dict, action: str, entity_type: str, entity_id: int | None, summary: str):
    con.execute(
        """INSERT INTO admin_activity(
               tournament_id,organizer_account_id,actor_email,action,entity_type,entity_id,summary
           ) VALUES(?,?,?,?,?,?,?)""",
        (
            int(tournament_id),
            None if int(actor["id"]) == OWNER_ACCOUNT_ID else int(actor["id"]),
            str(actor.get("email") or "CupNavi Owner"),
            str(action), str(entity_type), entity_id, str(summary),
        ),
    )


def tournament_members(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return all_rows(
        """SELECT oa.id,oa.email,oa.display_name,tm.role,tm.created_at
           FROM tournament_members tm
           JOIN organizer_accounts oa ON oa.id=tm.organizer_account_id
           WHERE tm.tournament_id=? AND oa.disabled_at IS NULL
           ORDER BY CASE tm.role WHEN 'owner' THEN 0 ELSE 1 END,
                    COALESCE(oa.display_name,oa.email),oa.id""",
        (int(tournament_id),),
    )


def add_tournament_member(actor: dict, tournament_id: int, values: dict):
    actor_id = int(actor["id"])
    if not _can_manage_members(actor_id, tournament_id):
        raise PermissionError("Endast cupens ägare kan hantera administratörer")
    email = normalize_email(values.get("email") or "")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Ange en giltig e-postadress")
    display_name = str(values.get("display_name") or "").strip() or None
    role = str(values.get("role") or "admin").strip().casefold()
    if role not in MEMBER_ROLES:
        raise ValueError("Ogiltig administratörsroll")

    temporary_password = None
    with connect() as con:
        row = con.execute(
            "SELECT id,disabled_at FROM organizer_accounts WHERE email=?", (email,)
        ).fetchone()
        if row:
            account_id = int(row[0])
            if row[1]:
                raise ValueError("Kontot är avstängt")
            if display_name:
                con.execute(
                    "UPDATE organizer_accounts SET display_name=COALESCE(NULLIF(display_name,''),?) WHERE id=?",
                    (display_name, account_id),
                )
        else:
            temporary_password = secrets.token_urlsafe(12)
            salt = os.urandom(16).hex()
            cursor = con.execute(
                """INSERT INTO organizer_accounts(email,display_name,password_salt,password_hash)
                   VALUES(?,?,?,?)""",
                (email, display_name, salt, password_hash(temporary_password, salt)),
            )
            account_id = int(cursor.lastrowid)
        con.execute(
            """INSERT INTO tournament_members(tournament_id,organizer_account_id,role)
               VALUES(?,?,?)
               ON CONFLICT(tournament_id,organizer_account_id) DO UPDATE SET
                 role=CASE WHEN tournament_members.role='owner' THEN 'owner' ELSE excluded.role END""",
            (int(tournament_id), account_id, role),
        )
        role_label = "cupägare" if role == "owner" else "lokal admin"
        _record_activity(con, tournament_id, actor, "member_added", "organizer", account_id, f"{email} lades till som {role_label}")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return {
        "member": one(
            """SELECT oa.id,oa.email,oa.display_name,tm.role,tm.created_at
               FROM tournament_members tm JOIN organizer_accounts oa ON oa.id=tm.organizer_account_id
               WHERE tm.tournament_id=? AND oa.id=?""",
            (int(tournament_id), account_id),
        ),
        "temporary_password": temporary_password,
    }


def update_tournament_member_role(actor: dict, tournament_id: int, member_id: int, role: str):
    actor_id = int(actor["id"])
    if not _can_manage_members(actor_id, tournament_id):
        raise PermissionError("Endast cupens ägare kan ändra roller")
    role = str(role or "").strip().casefold()
    if role not in MEMBER_ROLES:
        raise ValueError("Ogiltig administratörsroll")
    current = one(
        "SELECT role FROM tournament_members WHERE tournament_id=? AND organizer_account_id=?",
        (int(tournament_id), int(member_id)),
    )
    if not current:
        return None
    if current["role"] == "owner" and role != "owner":
        owners = one("SELECT COUNT(*) AS n FROM tournament_members WHERE tournament_id=? AND role='owner'", (int(tournament_id),))
        if int((owners or {}).get("n") or 0) <= 1:
            raise ValueError("Cupen måste ha minst en ägare")
    with connect() as con:
        con.execute(
            "UPDATE tournament_members SET role=? WHERE tournament_id=? AND organizer_account_id=?",
            (role, int(tournament_id), int(member_id)),
        )
        _record_activity(con, tournament_id, actor, "role_changed", "organizer", int(member_id), f"Rollen ändrades till {role}")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one(
        """SELECT oa.id,oa.email,oa.display_name,tm.role,tm.created_at
           FROM tournament_members tm JOIN organizer_accounts oa ON oa.id=tm.organizer_account_id
           WHERE tm.tournament_id=? AND oa.id=?""",
        (int(tournament_id), int(member_id)),
    )


def remove_tournament_member(actor: dict, tournament_id: int, member_id: int):
    actor_id = int(actor["id"])
    if not _can_manage_members(actor_id, tournament_id):
        raise PermissionError("Endast cupens ägare kan ta bort administratörer")
    current = one(
        """SELECT tm.role,oa.email FROM tournament_members tm
           JOIN organizer_accounts oa ON oa.id=tm.organizer_account_id
           WHERE tm.tournament_id=? AND tm.organizer_account_id=?""",
        (int(tournament_id), int(member_id)),
    )
    if not current:
        return None
    if int(member_id) == actor_id:
        raise ValueError("Du kan inte ta bort din egen åtkomst")
    if current["role"] == "owner":
        owners = one("SELECT COUNT(*) AS n FROM tournament_members WHERE tournament_id=? AND role='owner'", (int(tournament_id),))
        if int((owners or {}).get("n") or 0) <= 1:
            raise ValueError("Cupens sista ägare kan inte tas bort")
    with connect() as con:
        con.execute(
            "DELETE FROM tournament_members WHERE tournament_id=? AND organizer_account_id=?",
            (int(tournament_id), int(member_id)),
        )
        _record_activity(con, tournament_id, actor, "member_removed", "organizer", int(member_id), f"{current['email']} togs bort")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current


def tournament_activity(account_id: int, tournament_id: int, limit: int = 30):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return all_rows(
        """SELECT id,actor_email,action,entity_type,entity_id,summary,created_at
           FROM admin_activity WHERE tournament_id=? ORDER BY id DESC LIMIT ?""",
        (int(tournament_id), max(1, min(100, int(limit)))),
    )


def change_password(account_id: int, current_password: str, new_password: str):
    if int(account_id) == OWNER_ACCOUNT_ID:
        raise PermissionError("Plattformsägarens lösenord hanteras i driftmiljön")
    if len(str(new_password or "")) < 10:
        raise ValueError("Det nya lösenordet måste innehålla minst 10 tecken")
    account = one(
        "SELECT password_salt,password_hash FROM organizer_accounts WHERE id=? AND disabled_at IS NULL",
        (int(account_id),),
    )
    if not account or not hmac.compare_digest(password_hash(current_password, account["password_salt"]), str(account["password_hash"])):
        raise ValueError("Nuvarande lösenord är fel")
    salt = os.urandom(16).hex()
    with connect() as con:
        con.execute(
            "UPDATE organizer_accounts SET password_salt=?,password_hash=?,session_version=session_version+1 WHERE id=?",
            (salt, password_hash(new_password, salt), int(account_id)),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return True
