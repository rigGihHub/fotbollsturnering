import sqlite3
from pathlib import Path

from cupnavi_core.migrations import ensure_competition_class_schema_compat


def _partial_v14_database():
    con = sqlite3.connect(":memory:")
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY, age_classes_json TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, age_class TEXT);
        CREATE TABLE groups(id INTEGER PRIMARY KEY, tournament_id INTEGER, age_class TEXT);
        CREATE TABLE cupnavi_schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL);
        INSERT INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(14,'competition_classes_v124','2026-08-24T00:00:00');
        INSERT INTO tournaments(id,age_classes_json) VALUES(1,'["P2014"]');
        INSERT INTO teams(id,tournament_id,age_class) VALUES(1,1,'P2014');
        INSERT INTO groups(id,tournament_id,age_class) VALUES(1,1,'P2014');
        """
    )
    return con


def test_repair_when_v14_marker_exists_but_objects_are_missing():
    con = _partial_v14_database()
    ensure_competition_class_schema_compat(con)
    cols_team = {r[1] for r in con.execute("PRAGMA table_info(teams)")}
    cols_group = {r[1] for r in con.execute("PRAGMA table_info(groups)")}
    assert "competition_class_id" in cols_team
    assert "competition_class_id" in cols_group
    row = con.execute("SELECT id FROM competition_classes WHERE tournament_id=1 AND name='P2014'").fetchone()
    assert row is not None
    assert con.execute("SELECT competition_class_id FROM teams WHERE id=1").fetchone()[0] == row[0]
    assert con.execute("SELECT competition_class_id FROM groups WHERE id=1").fetchone()[0] == row[0]


def test_runtime_path_has_self_healing_schema_repair():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "ensure_competition_class_schema_compat(con)" in text
    assert "except Exception:" in text[text.index("def competition_classes"):text.index("def sync_competition_classes")]
    assert "ensure_competition_class_schema_compat(con)" in text
