import sqlite3

import pytest

from cupnavi_api.main import app
from cupnavi_api.venue_admin_repository import (
    admin_venues,
    update_pitch,
    update_pitch_window,
    update_venue_rules,
)


def _schema(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE tournament_members (
            organizer_account_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL
        );
        CREATE TABLE tournaments (
            id INTEGER PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            tournament_date TEXT,
            schedule_dirty INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE schedule_rules (
            tournament_id INTEGER PRIMARY KEY,
            pitch_count INTEGER NOT NULL DEFAULT 2,
            first_match_time TEXT NOT NULL DEFAULT '09:00',
            latest_kickoff_time TEXT NOT NULL DEFAULT '18:00',
            synchronized_pitch_times INTEGER NOT NULL DEFAULT 0,
            consider_pitch_travel INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE pitches (
            tournament_id INTEGER NOT NULL,
            pitch_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            address_verified INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(tournament_id,pitch_number)
        );
        CREATE TABLE pitch_day_windows (
            tournament_id INTEGER NOT NULL,
            pitch_number INTEGER NOT NULL,
            play_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            confirmed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(tournament_id,pitch_number,play_date)
        );
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            scheduled_start TEXT,
            pitch_number INTEGER
        );
        INSERT INTO tournament_members(organizer_account_id,tournament_id) VALUES(1,10);
        INSERT INTO tournaments(id,start_date,end_date,tournament_date) VALUES(10,'2026-09-19','2026-09-20','2026-09-19');
        INSERT INTO schedule_rules(tournament_id,pitch_count) VALUES(10,2);
        """
    )
    con.commit()
    con.close()


def _env(monkeypatch, tmp_path):
    database = tmp_path / "v632.sqlite"
    _schema(database)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(database))
    return database


def test_venue_setup_reuses_existing_schedule_tables(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    payload = admin_venues(1, 10)
    assert payload["rules"]["pitch_count"] == 2
    assert [pitch["name"] for pitch in payload["pitches"]] == ["Plan 1", "Plan 2"]
    assert len(payload["windows"]) == 4

    named = update_pitch(1, 10, 1, {"name": "Huvudplan", "address": "Idrottsvägen 1"})
    assert named["pitches"][0]["name"] == "Huvudplan"

    changed = update_pitch_window(
        1, 10, 1, "2026-09-19", {"start_time": "08:30", "end_time": "17:15", "confirmed": True}
    )
    row = next(item for item in changed["windows"] if item["pitch_number"] == 1 and item["play_date"] == "2026-09-19")
    assert row["start_time"] == "08:30"
    assert row["end_time"] == "17:15"
    assert bool(row["confirmed"])


def test_existing_schedule_is_never_silently_invalidated(monkeypatch, tmp_path):
    database = _env(monkeypatch, tmp_path)
    con = sqlite3.connect(database)
    con.execute(
        "INSERT INTO matches(tournament_id,scheduled_start,pitch_number) VALUES(10,'2026-09-19T10:00:00',2)"
    )
    con.commit()
    con.close()

    with pytest.raises(ValueError, match="plan 2"):
        update_venue_rules(1, 10, {"pitch_count": 1})

    saved = update_venue_rules(1, 10, {"pitch_count": 3, "first_match_time": "08:00", "latest_kickoff_time": "19:00"})
    assert saved["scheduled_count"] == 1
    assert saved["schedule_dirty"] is True

    con = sqlite3.connect(database)
    row = con.execute("SELECT scheduled_start,pitch_number FROM matches WHERE tournament_id=10").fetchone()
    con.close()
    assert row == ("2026-09-19T10:00:00", 2)


def test_invalid_pitch_window_is_rejected(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="senare än starttiden"):
        update_pitch_window(1, 10, 1, "2026-09-19", {"start_time": "17:00", "end_time": "09:00"})
    with pytest.raises(ValueError, match="utanför cupens datumintervall"):
        update_pitch_window(1, 10, 1, "2026-09-21", {"start_time": "09:00", "end_time": "17:00"})


def test_venue_routes_are_exposed():
    routes = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    assert ("/api/admin/cups/{tournament_id}/venues", "GET") in routes
    assert ("/api/admin/cups/{tournament_id}/venues/rules", "PUT") in routes
    assert ("/api/admin/cups/{tournament_id}/venues/pitches/{pitch_number}", "PUT") in routes
    assert ("/api/admin/cups/{tournament_id}/venues/pitches/{pitch_number}/windows/{play_date}", "PUT") in routes
