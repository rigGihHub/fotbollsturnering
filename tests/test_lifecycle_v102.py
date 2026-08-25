import sqlite3
from pathlib import Path

from cupnavi_core.lifecycle import (
    choose_unique_slug,
    is_editable_status,
    is_public_status,
    normalize_status,
    slug_base,
    status_label,
)
from cupnavi_core.migrations import LATEST_SCHEMA_VERSION, apply_migrations


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def _legacy_schema(con):
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,is_published INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER);
        CREATE TABLE players(id INTEGER PRIMARY KEY,team_id INTEGER);
        CREATE TABLE referees(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE brackets(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,scheduled_start TEXT);
        CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER);
        CREATE TABLE feedback(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE offers(id INTEGER PRIMARY KEY,tournament_id INTEGER,active INTEGER,sort_order INTEGER);
        """
    )


def test_lifecycle_status_contract_is_language_neutral():
    assert normalize_status(None, is_published=False) == "draft"
    assert normalize_status(None, is_published=True) == "published"
    assert status_label("completed", "sv") == "Avslutad"
    assert status_label("completed", "en") == "Completed"
    assert is_public_status("completed")
    assert not is_editable_status("completed")


def test_public_slug_is_stable_readable_and_unique():
    assert slug_base("Örebro Cupen", "2027-06-12") == "orebro-cupen-2027"
    assert choose_unique_slug("Örebro Cupen", "2027-06-12", 42, set()) == "orebro-cupen-2027"
    assert choose_unique_slug("Örebro Cupen", "2027-06-12", 42, {"orebro-cupen-2027"}) == "orebro-cupen-2027-42"


def test_schema_v8_adds_lifecycle_history_fields():
    con = sqlite3.connect(":memory:")
    _legacy_schema(con)
    apply_migrations(con)
    columns = {row[1] for row in con.execute("PRAGMA table_info(tournaments)")}
    assert LATEST_SCHEMA_VERSION >= 8
    assert {"lifecycle_status", "public_slug", "completed_at", "trashed_at"} <= columns


def test_completed_cups_remain_public_and_admin_is_write_protected():
    text = app_text()
    assert "IN ('published','live','completed')" in text
    assert 'tournament_lifecycle == "completed"' in text
    assert "Adminläget är skrivskyddat tills cupen återöppnas" in text
    assert "Återöppna cup" in text


def test_lifecycle_transitions_and_safe_trash_exist():
    text = app_text()
    assert "Markera cupen som pågående" in text
    assert "Avsluta cup" in text
    assert "lifecycle_status='completed'" in text
    assert "Flytta cupen till papperskorgen" in text
    assert "Återställ cup" in text
    assert "Radera permanent" in text
    assert "typed_name != bin_name" in text


def test_public_links_prefer_permanent_slug_but_keep_numeric_compatibility():
    text = app_text()
    assert "SELECT public_slug FROM tournaments WHERE id=?" in text
    assert "requested_cup_id = int(cup_query_text)" in text
    assert 'row["public_slug"] == cup_query_text' in text
