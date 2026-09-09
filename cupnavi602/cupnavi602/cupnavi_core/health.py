"""Tekniska hälsokontroller som inte innehåller Streamlit-kod."""

from .migrations import LATEST_SCHEMA_VERSION, current_schema_version

CRITICAL_TABLES = (
    "tournaments",
    "groups",
    "teams",
    "players",
    "referees",
    "matches",
    "player_match_stats",
    "schedule_rules",
    "offers",
    "sponsors",
    "functionaries",
    "visitor_sessions",
    "audit_log",
    "cup_feed",
    "notifications",
    "venue_points",
    "referee_acknowledgements",
)


def _table_names(con):
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def collect_database_health(con):
    existing = _table_names(con)
    missing = [table for table in CRITICAL_TABLES if table not in existing]
    version = current_schema_version(con)

    return {
        "ok": not missing and version == LATEST_SCHEMA_VERSION,
        "schema_version": version,
        "latest_schema_version": LATEST_SCHEMA_VERSION,
        "missing_tables": missing,
    }
