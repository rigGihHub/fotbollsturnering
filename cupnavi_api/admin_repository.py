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
from .repository import all_rows, connect, one, with_imported_location

CUPINFO_FIELDS = (
    "name",
    "start_date",
    "end_date",
    "organizer",
    "arena_address",
    "organizer_phone",
    "feedback_email",
    "public_information",
    "arrangement_type",
    "show_public_weather", "show_public_weather_configured", "show_public_kits", "show_public_away_kits", "show_public_logos", "show_public_goal_minutes",
)
CUPINFO_OPTIONAL_TEXT_FIELDS = (
    "organizer",
    "arena_address",
    "organizer_phone",
    "feedback_email",
    "public_information",
    "arrangement_type",
)

TEAM_FIELDS = (
    "name", "age_class", "primary_color", "secondary_color",
    "home_pattern", "home_color_2", "away_pattern", "away_color_2",
    "logo_url", "logo_source_url",
)
TEAM_PROJECTION = (
    "id,tournament_id,name,group_id,age_class,primary_color,secondary_color,"
    "home_pattern,home_color_2,away_pattern,away_color_2,logo_url,logo_source_url"
)
KIT_PATTERNS = {"Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad", "Diagonala ränder", "Grafiskt"}
HIDDEN_LIFECYCLE_STATUSES = ("trashed", "purged")


class ConcurrentUpdateError(ValueError):
    """The client attempted to save an older tournament revision."""


def ensure_team_kit_schema() -> None:
    """Bring API-only and older databases up to the established kit schema."""
    columns = _table_columns("teams")
    if not columns:
        return
    statements = {
        "home_pattern": "ALTER TABLE teams ADD COLUMN home_pattern TEXT NOT NULL DEFAULT 'Helfärgad'",
        "home_color_2": "ALTER TABLE teams ADD COLUMN home_color_2 TEXT NOT NULL DEFAULT '#FFFFFF'",
        "away_pattern": "ALTER TABLE teams ADD COLUMN away_pattern TEXT NOT NULL DEFAULT 'Helfärgad'",
        "away_color_2": "ALTER TABLE teams ADD COLUMN away_color_2 TEXT NOT NULL DEFAULT '#111827'",
        "logo_url": "ALTER TABLE teams ADD COLUMN logo_url TEXT",
        "logo_source_url": "ALTER TABLE teams ADD COLUMN logo_source_url TEXT",
    }
    missing = [name for name in statements if name not in columns]
    if not missing:
        return
    with connect() as con:
        for name in missing:
            con.execute(statements[name])
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def ensure_club_registry_schema() -> None:
    """Persistent, reusable club knowledge shared by future cups."""
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS club_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            home_pattern TEXT,
            home_color_1 TEXT,
            home_color_2 TEXT,
            away_pattern TEXT,
            away_color_1 TEXT,
            away_color_2 TEXT,
            logo_url TEXT,
            logo_source_url TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        commit=getattr(con,"commit",None)
        if callable(commit): commit()


def club_registry_lookup(team_name: str):
    ensure_club_registry_schema()
    key=" ".join(str(team_name or "").casefold().split())
    row=one("SELECT * FROM club_registry WHERE normalized_name=?",(key,))
    if row: return row
    # Youth suffixes commonly follow the base club name; longest known prefix wins.
    rows=all_rows("SELECT * FROM club_registry ORDER BY LENGTH(normalized_name) DESC")
    return next((row for row in rows if key.startswith(str(row.get("normalized_name") or "")+" ")),None)


def club_registry_remember(team: dict) -> None:
    ensure_club_registry_schema()
    name=" ".join(str(team.get("name") or "").strip().split())
    if not name: return
    key=name.casefold()
    with connect() as con:
        con.execute("""INSERT INTO club_registry
            (normalized_name,display_name,home_pattern,home_color_1,home_color_2,away_pattern,away_color_1,away_color_2,logo_url,logo_source_url,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(normalized_name) DO UPDATE SET
              display_name=excluded.display_name,
              home_pattern=COALESCE(excluded.home_pattern,club_registry.home_pattern),
              home_color_1=COALESCE(excluded.home_color_1,club_registry.home_color_1),
              home_color_2=COALESCE(excluded.home_color_2,club_registry.home_color_2),
              away_pattern=COALESCE(excluded.away_pattern,club_registry.away_pattern),
              away_color_1=COALESCE(excluded.away_color_1,club_registry.away_color_1),
              away_color_2=COALESCE(excluded.away_color_2,club_registry.away_color_2),
              logo_url=COALESCE(excluded.logo_url,club_registry.logo_url),
              logo_source_url=COALESCE(excluded.logo_source_url,club_registry.logo_source_url),
              updated_at=CURRENT_TIMESTAMP""",(
            key,name,team.get("home_pattern"),team.get("primary_color"),team.get("home_color_2"),
            team.get("away_pattern"),team.get("secondary_color"),team.get("away_color_2"),team.get("logo_url"),team.get("logo_source_url")
        ))
        commit=getattr(con,"commit",None)
        if callable(commit): commit()


def _table_columns(table_name: str) -> set[str]:
    """Return columns without assuming that every lifecycle migration exists yet."""
    rows = all_rows(f"PRAGMA table_info({table_name})")
    return {str(row.get("name")) for row in rows if row.get("name")}


def _ensure_cupinfo_columns() -> set[str]:
    """Repair legacy tournament schemas before Cupinfo is read or written.

    Older CupNavi databases can predate the descriptive Cupinfo fields. The API
    must not crash merely because the database was created before those columns
    existed. Add only the known optional TEXT columns and leave core identity,
    dates and publishing columns to the normal schema migrations.
    """
    columns = _table_columns("tournaments")
    if not columns:
        return columns
    missing = [field for field in CUPINFO_OPTIONAL_TEXT_FIELDS if field not in columns]
    boolean_defaults={"show_public_weather":1,"show_public_weather_configured":0,"show_public_kits":1,"show_public_away_kits":1,"show_public_logos":1,"show_public_goal_minutes":0}
    with connect() as con:
        for field,default in boolean_defaults.items():
            if field not in columns:
                con.execute(f"ALTER TABLE tournaments ADD COLUMN {field} INTEGER NOT NULL DEFAULT {default}")
        for field in missing:
            if field == "arrangement_type":
                con.execute("ALTER TABLE tournaments ADD COLUMN arrangement_type TEXT NOT NULL DEFAULT 'tournament'")
            else:
                con.execute(f"ALTER TABLE tournaments ADD COLUMN {field} TEXT")
        if "admin_revision" not in columns:
            con.execute("ALTER TABLE tournaments ADD COLUMN admin_revision INTEGER NOT NULL DEFAULT 1")
        if "created_at" not in columns:
            con.execute("ALTER TABLE tournaments ADD COLUMN created_at TEXT")
            con.execute("UPDATE tournaments SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL OR TRIM(created_at)=''")
        con.execute("""CREATE TABLE IF NOT EXISTS admin_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            organizer_account_id INTEGER,
            actor_email TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _table_columns("tournaments")


def authenticate_organizer(email: str, password: str):
    owner = authenticate_owner(email, password)
    if owner:
        return owner
    normalized_email = normalize_email(email)
    session_projection = "session_version" if "session_version" in _table_columns("organizer_accounts") else "1 AS session_version"
    account = one(
        f"""SELECT id,email,display_name,password_salt,password_hash,disabled_at,{session_projection}
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
    session_projection = "session_version" if "session_version" in _table_columns("organizer_accounts") else "1 AS session_version"
    row = one(
        f"SELECT id,email,display_name,disabled_at,{session_projection} FROM organizer_accounts WHERE id=?",
        (int(account_id),),
    )
    if not row or row.get("disabled_at"):
        return None
    return {
        "id": int(row["id"]),
        "email": normalize_email(row["email"]),
        "display_name": row.get("display_name"),
        "session_version": int(row.get("session_version") or 1),
    }


def organizer_tournaments(account_id: int):
    _ensure_cupinfo_columns()
    if int(account_id) == OWNER_ACCOUNT_ID:
        rows = all_rows(
            """SELECT id,name,public_slug,start_date,end_date,is_published,created_at
               FROM tournaments
               WHERE COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')
               ORDER BY COALESCE(start_date,''),name,id"""
        )
        for row in rows:
            row["role"] = "owner"
        return rows
    return all_rows(
        """SELECT t.id,t.name,t.public_slug,t.start_date,t.end_date,t.is_published,t.created_at,tm.role
           FROM tournament_members tm
           JOIN tournaments t ON t.id=tm.tournament_id
           WHERE tm.organizer_account_id=?
             AND COALESCE(t.lifecycle_status,'draft') NOT IN ('trashed','purged')
           ORDER BY COALESCE(t.start_date,''),t.name,t.id""",
        (int(account_id),),
    )


def trashed_tournaments(account_id: int):
    """Return the platform trash or cups owned by the current organizer."""
    if int(account_id) == OWNER_ACCOUNT_ID:
        rows = all_rows(
            """SELECT id,name,public_slug,start_date,end_date,is_published,trashed_at
               FROM tournaments WHERE COALESCE(lifecycle_status,'draft')='trashed'
               ORDER BY COALESCE(trashed_at,'') DESC,name,id"""
        )
    else:
        rows = all_rows(
            """SELECT t.id,t.name,t.public_slug,t.start_date,t.end_date,t.is_published,t.trashed_at
               FROM tournaments t JOIN tournament_members tm ON tm.tournament_id=t.id
               WHERE tm.organizer_account_id=? AND tm.role='owner'
                 AND COALESCE(t.lifecycle_status,'draft')='trashed'
               ORDER BY COALESCE(t.trashed_at,'') DESC,t.name,t.id""",
            (int(account_id),),
        )
    for row in rows:
        row["role"] = "owner"
    return rows


def purge_trashed_tournaments(account_id: int) -> int:
    """Empty only the trash visible to the current cup owner.

    Purged cups are kept as hidden tombstones instead of deleting relational data.
    They are no longer listed, restorable, accessible in admin or published.
    """
    account_id = int(account_id)
    with connect() as con:
        if account_id == OWNER_ACCOUNT_ID:
            cursor = con.execute(
                """UPDATE tournaments
                   SET lifecycle_status='purged',trashed_at=NULL,is_published=0
                   WHERE COALESCE(lifecycle_status,'draft')='trashed'"""
            )
        else:
            cursor = con.execute(
                """UPDATE tournaments
                   SET lifecycle_status='purged',trashed_at=NULL,is_published=0
                   WHERE COALESCE(lifecycle_status,'draft')='trashed'
                     AND id IN (
                         SELECT tournament_id FROM tournament_members
                         WHERE organizer_account_id=? AND role='owner'
                     )""",
                (account_id,),
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
    columns = _ensure_cupinfo_columns()
    required = ("id", "public_slug", "is_published", "name", "start_date", "end_date", "admin_revision")
    missing_required = [field for field in required if field not in columns]
    if missing_required:
        raise RuntimeError(f"Tournament schema missing required columns: {','.join(missing_required)}")
    fields = ",".join((*required, *CUPINFO_OPTIONAL_TEXT_FIELDS, "show_public_weather", "show_public_weather_configured", "show_public_kits", "show_public_away_kits", "show_public_logos", "show_public_goal_minutes"))
    return with_imported_location(one(f"SELECT {fields} FROM tournaments WHERE id=?", (int(tournament_id),)))


def update_cupinfo(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    columns = _ensure_cupinfo_columns()
    clean = {}
    boolean_fields={"show_public_weather","show_public_weather_configured","show_public_kits","show_public_away_kits","show_public_logos","show_public_goal_minutes"}
    for field in CUPINFO_FIELDS:
        if field not in values or field not in columns:
            continue
        value = values[field]
        if field in boolean_fields:
            clean[field]=1 if bool(value) else 0
            continue
        if value is None:
            clean[field] = None
        else:
            text = str(value).strip()
            clean[field] = text or None
    if "name" in clean and not clean["name"]:
        raise ValueError("Cupnamn krävs")
    if "arrangement_type" in clean and clean["arrangement_type"] not in {"matchcamp", "tournament", "tournament_playoffs", "custom"}:
        raise ValueError("Ogiltig arrangemangstyp")
    if "show_public_weather" in clean and "show_public_weather_configured" in columns:
        clean["show_public_weather_configured"] = 1
    expected_revision = values.get("expected_revision")
    if expected_revision is not None:
        try:
            expected_revision = int(expected_revision)
        except (TypeError, ValueError) as exc:
            raise ValueError("Ogiltig versionskontroll") from exc
    if clean:
        assignments = ",".join(f"{field}=?" for field in clean)
        params = [clean[field] for field in clean]
        where = "id=?"
        params.append(int(tournament_id))
        if expected_revision is not None:
            where += " AND admin_revision=?"
            params.append(expected_revision)
        with connect() as con:
            cursor = con.execute(
                f"UPDATE tournaments SET {assignments},admin_revision=admin_revision+1 WHERE {where}",
                tuple(params),
            )
            rowcount = getattr(cursor, "rowcount", None)
            revision_conflict = expected_revision is not None and rowcount is not None and int(rowcount) == 0
            if expected_revision is not None and (rowcount is None or int(rowcount) < 0):
                revision_row = con.execute("SELECT admin_revision FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
                revision_conflict = not revision_row or int(revision_row[0]) != expected_revision + 1
            if revision_conflict:
                rollback = getattr(con, "rollback", None)
                if callable(rollback):
                    rollback()
                raise ConcurrentUpdateError("Cupinfo har ändrats av en annan administratör. Ladda om innan du sparar igen.")
            actor = organizer_account(int(account_id)) or {"email": "CupNavi Owner"}
            con.execute(
                """INSERT INTO admin_activity(
                       tournament_id,organizer_account_id,actor_email,action,entity_type,entity_id,summary
                   ) VALUES(?,?,?,?,?,?,?)""",
                (int(tournament_id), None if int(account_id) == OWNER_ACCOUNT_ID else int(account_id), str(actor.get("email") or "CupNavi Owner"), "updated", "cupinfo", int(tournament_id), "Cupinformationen uppdaterades"),
            )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
    return admin_cupinfo(account_id, tournament_id)


def trash_tournament(account_id: int, tournament_id: int, confirmed_name: str):
    """Move one cup to recoverable trash. Tournament owners only."""
    if int(account_id) != OWNER_ACCOUNT_ID and not one(
        "SELECT 1 AS ok FROM tournament_members WHERE tournament_id=? AND organizer_account_id=? AND role='owner'",
        (int(tournament_id), int(account_id)),
    ):
        raise PermissionError("Endast cupens ägare kan ta bort cupen")
    current = one(
        """SELECT id,name,public_slug,start_date,end_date,is_published
           FROM tournaments
           WHERE id=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')""",
        (int(tournament_id),),
    )
    if not current:
        return None
    if str(confirmed_name or "").strip() != str(current["name"]):
        raise ValueError("Cupnamnet stämmer inte")
    with connect() as con:
        cursor = con.execute(
            """UPDATE tournaments
               SET lifecycle_status='trashed',trashed_at=CURRENT_TIMESTAMP,is_published=0
               WHERE id=? AND name=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')""",
            (int(tournament_id), current["name"]),
        )
        rowcount = getattr(cursor, "rowcount", None)
        if rowcount is not None and rowcount >= 0 and rowcount != 1:
            rollback = getattr(con,"rollback",None)
            if callable(rollback):
                rollback()
            return None
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return current


def restore_tournament(account_id: int, tournament_id: int):
    """Restore a trashed cup as an unpublished draft. Owner only."""
    if int(account_id) != OWNER_ACCOUNT_ID and not one(
        "SELECT 1 AS ok FROM tournament_members WHERE tournament_id=? AND organizer_account_id=? AND role='owner'",
        (int(tournament_id), int(account_id)),
    ):
        raise PermissionError("Endast cupens ägare kan återställa cupen")
    current = one(
        """SELECT id,name,public_slug,start_date,end_date,is_published,trashed_at
           FROM tournaments
           WHERE id=? AND COALESCE(lifecycle_status,'draft')='trashed'""",
        (int(tournament_id),),
    )
    if not current:
        return None
    with connect() as con:
        cursor = con.execute(
            """UPDATE tournaments
               SET lifecycle_status='draft',trashed_at=NULL,is_published=0
               WHERE id=? AND COALESCE(lifecycle_status,'draft')='trashed'""",
            (int(tournament_id),),
        )
        rowcount = getattr(cursor, "rowcount", None)
        if rowcount is not None and rowcount >= 0 and rowcount != 1:
            rollback = getattr(con, "rollback", None)
            if callable(rollback):
                rollback()
            return None
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    restored = dict(current)
    restored["is_published"] = 0
    restored["trashed_at"] = None
    restored["role"] = "owner"
    return restored


def admin_teams(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    ensure_team_kit_schema()
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
    for field in ("primary_color", "secondary_color", "home_color_2", "away_color_2"):
        color = clean.get(field)
        if color is not None and (
            len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:])
        ):
            raise ValueError("Lagfärger måste anges som #RRGGBB")
    for field in ("home_pattern", "away_pattern"):
        if clean.get(field) is not None and clean[field] not in KIT_PATTERNS:
            raise ValueError("Okänt tröjmönster")
    for field in ("logo_url", "logo_source_url"):
        if clean.get(field) is not None and not clean[field].startswith("https://"):
            raise ValueError("Logotyplänkar måste använda HTTPS")
    return clean


def _team(account_id: int, tournament_id: int, team_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    ensure_team_kit_schema()
    return one(
        f"SELECT {TEAM_PROJECTION} FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )


def create_team(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    ensure_team_kit_schema()
    clean = _clean_team(values, require_name=True)
    clean.setdefault("age_class", None)
    clean.setdefault("primary_color", "#111827")
    clean.setdefault("secondary_color", "#FFFFFF")
    clean.setdefault("home_pattern", "Helfärgad")
    clean.setdefault("home_color_2", "#FFFFFF")
    clean.setdefault("away_pattern", "Helfärgad")
    clean.setdefault("away_color_2", "#111827")
    clean.setdefault("logo_url", None)
    clean.setdefault("logo_source_url", None)
    with connect() as con:
        duplicate = con.execute(
            "SELECT id FROM teams WHERE tournament_id=? AND lower(trim(name))=lower(?)",
            (int(tournament_id), clean["name"]),
        ).fetchone()
        if duplicate:
            raise ValueError("Det finns redan ett lag med samma namn")
        cursor = con.execute(
            """INSERT INTO teams(tournament_id,name,age_class,primary_color,secondary_color,
                                  home_pattern,home_color_2,away_pattern,away_color_2,logo_url,logo_source_url)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (int(tournament_id), clean["name"], clean["age_class"], clean["primary_color"], clean["secondary_color"],
             clean["home_pattern"], clean["home_color_2"], clean["away_pattern"], clean["away_color_2"],clean["logo_url"],clean["logo_source_url"]),
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
