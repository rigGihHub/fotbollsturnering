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
}


def _table_columns(table_name: str) -> set[str]:
    rows = all_rows(f"PRAGMA table_info({table_name})")
    return {str(row.get("name")) for row in rows if row.get("name")}


def _duplicate_column_error(exc: Exception) -> bool:
    message = str(exc).casefold()
    return "duplicate column" in message or "already exists" in message


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

    return columns
