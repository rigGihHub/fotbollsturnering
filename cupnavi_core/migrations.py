"""Versionsstyrda databasmigreringar för CupNavi.

Regel:
- En migration får aldrig ändras efter att den släppts.
- Nya schemaändringar läggs till med ett nytt versionsnummer.
- Migreringar ska vara idempotenta där det är rimligt och köras i stigande ordning.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

LATEST_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS = (
    Migration(
        1,
        "baseline_version_tracking",
        (),
    ),
    Migration(
        2,
        "performance_indexes",
        (
            "CREATE INDEX IF NOT EXISTS idx_groups_tournament ON groups(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_tournament ON teams(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_group ON teams(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_referees_tournament ON referees(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_tournament_start ON matches(tournament_id, scheduled_start)",
            "CREATE INDEX IF NOT EXISTS idx_matches_group ON matches(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_bracket ON matches(bracket_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_stats_match ON player_match_stats(match_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_tournament ON feedback(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_offers_tournament_active_order ON offers(tournament_id, active, sort_order)",
        ),
    ),
)


def _execute(con, sql, params=()):
    return con.execute(sql, params)


def ensure_migration_table(con):
    _execute(
        con,
        """
        CREATE TABLE IF NOT EXISTS cupnavi_schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """,
    )


def current_schema_version(con):
    ensure_migration_table(con)
    row = _execute(
        con,
        "SELECT COALESCE(MAX(version), 0) FROM cupnavi_schema_migrations",
    ).fetchone()
    return int(row[0] if row is not None else 0)


def apply_migrations(con):
    """Applicera alla saknade migreringar och returnera nya versionsnummer."""
    ensure_migration_table(con)
    current = current_schema_version(con)
    applied = []

    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        for statement in migration.statements:
            _execute(con, statement)
        _execute(
            con,
            "INSERT INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(?,?,?)",
            (
                migration.version,
                migration.name,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        applied.append(migration.version)
    return applied
