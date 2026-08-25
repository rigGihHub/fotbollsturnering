from pathlib import Path
import sqlite3

from cupnavi_core.migrations import MIGRATIONS, LATEST_SCHEMA_VERSION


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_competition_class_language_and_hierarchy_are_visible():
    text = app_text()
    assert "Tävlingsklasser i turneringen" in text
    assert '"Tävlingsklass"' in text
    assert 'filter_mode == "Tävlingsklass"' in text
    assert "En cup kan innehålla flera sportsligt separata tävlingar" in text
    assert "competition_classes(tournament_id)" in text


def test_new_and_cloned_tournaments_sync_class_objects():
    text = app_text()
    assert "sync_competition_classes(new_tournament_id" in text
    assert "sync_competition_classes(new_id" in text
    assert "competition_class_id" in text


def test_schema_v14_has_real_competition_class_objects_and_backfill():
    assert LATEST_SCHEMA_VERSION >= 14
    migration = next(m for m in MIGRATIONS if m.version == 14)
    joined = "\n".join(migration.statements)
    assert "CREATE TABLE IF NOT EXISTS competition_classes" in joined
    assert "ALTER TABLE teams ADD COLUMN competition_class_id" in joined
    assert "ALTER TABLE groups ADD COLUMN competition_class_id" in joined
    assert "UPDATE teams SET competition_class_id" in joined
    assert "UPDATE groups SET competition_class_id" in joined

    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY, age_classes_json TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, age_class TEXT);
        CREATE TABLE groups(id INTEGER PRIMARY KEY, tournament_id INTEGER, age_class TEXT);
        INSERT INTO tournaments(id,age_classes_json) VALUES(1,'["P2014","F2014"]');
        INSERT INTO teams(id,tournament_id,age_class) VALUES(1,1,'P2014');
        INSERT INTO groups(id,tournament_id,age_class) VALUES(1,1,'P2014');
    """)
    for statement in migration.statements:
        con.execute(statement)
    class_row = con.execute("SELECT id,name FROM competition_classes WHERE tournament_id=1 AND name='P2014'").fetchone()
    assert class_row is not None
    assert con.execute("SELECT competition_class_id FROM teams WHERE id=1").fetchone()[0] == class_row[0]
    assert con.execute("SELECT competition_class_id FROM groups WHERE id=1").fetchone()[0] == class_row[0]
