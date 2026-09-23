"""Small idempotent runtime migrations for legacy CupNavi databases.

The production database predates parts of the current admin model. Keep these
repairs deliberately narrow: only additive columns that current code already
expects are created here. Unknown schema problems must still fail loudly.
"""
from __future__ import annotations

from .repository import all_rows, connect

TOURNAMENT_RUNTIME_COLUMNS = {
    "organizer": "TEXT",
    "arena_address": "TEXT",
    "organizer_phone": "TEXT",
    "feedback_email": "TEXT",
    "public_information": "TEXT",
    "lifecycle_status": "TEXT DEFAULT 'draft'",
    "trashed_at": "TEXT",
    "admin_revision": "INTEGER NOT NULL DEFAULT 1",
    "show_public_goal_minutes": "INTEGER NOT NULL DEFAULT 0",
}


def _table_columns(table_name: str) -> set[str]:
    rows = all_rows(f"PRAGMA table_info({table_name})")
    return {str(row.get("name")) for row in rows if row.get("name")}


def _duplicate_column_error(exc: Exception) -> bool:
    message = str(exc).casefold()
    return "duplicate column" in message or "already exists" in message


def ensure_goal_minutes_table(con) -> None:
    con.execute("""CREATE TABLE IF NOT EXISTS match_goal_minutes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
        side TEXT NOT NULL CHECK(side IN ('home','away')),
        minute INTEGER NOT NULL CHECK(minute BETWEEN 1 AND 300)
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_match_goal_minutes_match ON match_goal_minutes(match_id,id)")


def ensure_runtime_schema() -> set[str]:
    """Make the legacy tournaments table compatible with the active admin API.

    Safe to run repeatedly and safe if two application instances start at nearly
    the same time. Each ALTER is committed independently so one already-created
    column cannot roll back unrelated repairs.
    """
    columns = _table_columns("tournaments")
    if not columns:
        return columns

    for column, definition in TOURNAMENT_RUNTIME_COLUMNS.items():
        if column in columns:
            continue
        try:
            with connect() as con:
                con.execute(f"ALTER TABLE tournaments ADD COLUMN {column} {definition}")
                commit = getattr(con, "commit", None)
                if callable(commit):
                    commit()
        except Exception as exc:
            # A second instance may have completed the same additive migration
            # after our initial PRAGMA read. Ignore only that precise race.
            refreshed = _table_columns("tournaments")
            if column not in refreshed and not _duplicate_column_error(exc):
                raise
        columns = _table_columns("tournaments")

    from cupnavi_core.pitch_availability import ensure_pitch_intervals_schema
    with connect() as con:
        ensure_pitch_intervals_schema(con)
        con.commit()

    account_columns = _table_columns("organizer_accounts")
    if account_columns and "session_version" not in account_columns:
        try:
            with connect() as con:
                con.execute("ALTER TABLE organizer_accounts ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1")
                commit = getattr(con, "commit", None)
                if callable(commit):
                    commit()
        except Exception as exc:
            refreshed = _table_columns("organizer_accounts")
            if "session_version" not in refreshed and not _duplicate_column_error(exc):
                raise

    with connect() as con:
        ensure_goal_minutes_table(con)
        con.execute("""CREATE TABLE IF NOT EXISTS admin_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            organizer_account_id INTEGER,
            actor_email TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_admin_activity_tournament_created "
            "ON admin_activity(tournament_id,created_at,id)"
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return columns
