import ast
import sqlite3
from datetime import datetime
from pathlib import Path


def _load_app_functions(*names):
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    module = ast.Module(body=wanted, type_ignores=[])
    namespace = {
        "sqlite3": sqlite3,
        "datetime": datetime,
        "CLOUD_DATABASE_ENABLED": False,
    }
    exec(compile(module, "app.py", "exec"), namespace)
    return namespace


def test_old_tournament_row_without_sport_defaults_to_football():
    ns = _load_app_functions("_row_value")
    row_value = ns["_row_value"]
    legacy_row = {"id": 1, "name": "Äldre cup"}
    assert row_value(legacy_row, "sport", "Fotboll") == "Fotboll"
    assert row_value({"sport": "Innebandy"}, "sport", "Fotboll") == "Innebandy"


def test_v96_compat_schema_repairs_legacy_database_and_marks_migration():
    ns = _load_app_functions(
        "_rows_from_cursor",
        "execute_script",
        "_connection_columns",
        "ensure_v96_experience_schema_compat",
    )
    ensure = ns["ensure_v96_experience_schema_compat"]

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
        CREATE TABLE referees(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
        CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER, scheduled_start TEXT);
        INSERT INTO tournaments(id,name) VALUES(1,'Legacy Cup');
        """
    )

    ensure(con)
    con.commit()

    tournament_columns = {row[1] for row in con.execute("PRAGMA table_info(tournaments)")}
    team_columns = {row[1] for row in con.execute("PRAGMA table_info(teams)")}
    match_columns = {row[1] for row in con.execute("PRAGMA table_info(matches)")}

    assert "sport" in tournament_columns
    assert "checked_in" in team_columns
    assert "checked_in_at" in team_columns
    assert "original_scheduled_start" in match_columns
    assert con.execute("SELECT sport FROM tournaments WHERE id=1").fetchone()[0] == "Fotboll"

    for table in (
        "audit_log",
        "cup_feed",
        "notifications",
        "venue_points",
        "referee_acknowledgements",
    ):
        assert con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()

    assert con.execute(
        "SELECT version FROM cupnavi_schema_migrations WHERE version=5"
    ).fetchone()[0] == 5

    # Idempotens: en andra körning får inte krascha eller ändra defaultvärdet.
    ensure(con)
    assert con.execute("SELECT sport FROM tournaments WHERE id=1").fetchone()[0] == "Fotboll"


def test_public_view_uses_safe_sport_lookup_and_has_release_integrity_guard():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "_row_value(tournament, 'sport', 'Fotboll')" in text
    assert '_row_value(tournament, "sport", "Fotboll")' in text
    assert "RELEASE_FILES_MISMATCH = CORE_APP_VERSION != APP_BUILD_VERSION" in text
    assert "Lägg in hela releasepaketet i GitHub, inte bara app.py." in text
