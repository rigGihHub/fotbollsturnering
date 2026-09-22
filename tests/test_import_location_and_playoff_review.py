import json
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cupnavi_api import repository, venue_admin_routes, playoff_import_repository, publish_reporting_repository


@pytest.fixture
def imported_cups(tmp_path, monkeypatch):
    path = tmp_path / "imports.db"
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE tournaments(id INTEGER PRIMARY KEY, name TEXT, arena_address TEXT,
                admin_revision INTEGER DEFAULT 0, arrangement_type TEXT DEFAULT 'tournament',
                start_date TEXT, playoff_format TEXT, bronze_match INTEGER,
                schedule_dirty INTEGER DEFAULT 0, is_published INTEGER DEFAULT 0);
            CREATE TABLE tournament_setup_imports(id INTEGER PRIMARY KEY, tournament_id INTEGER,
                import_kind TEXT, source_name TEXT, payload_json TEXT);
            CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
            CREATE TABLE groups(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
            CREATE TABLE pitches(tournament_id INTEGER, pitch_number INTEGER, name TEXT);
            CREATE TABLE brackets(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT, size INTEGER, bronze_match INTEGER);
            CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER, bracket_id INTEGER,
                stage TEXT, round_no INTEGER, match_no INTEGER, home_source TEXT, away_source TEXT,
                scheduled_start TEXT, pitch_number INTEGER, schedule_locked INTEGER);
            INSERT INTO tournaments(id,name,start_date) VALUES(1,'Cup 1','2026-10-24'),(2,'Cup 2','2026-10-24');
            INSERT INTO teams VALUES(1,1,'ÖSK'),(2,1,'AIK');
        """)

    @contextmanager
    def connect():
        con = sqlite3.connect(path)
        try:
            yield con
        finally:
            con.close()

    monkeypatch.setattr(repository, "connect", connect)
    monkeypatch.setattr(venue_admin_routes, "connect", connect)
    monkeypatch.setattr(venue_admin_routes, "admin_schedule", lambda account, cup: {} if cup == 1 else None)
    monkeypatch.setattr(playoff_import_repository, "connect", connect)
    monkeypatch.setattr(playoff_import_repository, "_has_tournament_access", lambda account, cup: cup == 1)
    return connect


def client():
    app = FastAPI()
    venue_admin_routes.register_venue_admin_routes(app, lambda authorization: {"id": 7})
    return TestClient(app)


def test_import_persists_location_once_and_preserves_manual_correction(imported_cups):
    api = client()
    request = {"proposal": {"location": " Sörbyvallen, Örebro "}}
    for _ in range(2):
        assert api.post("/api/admin/cups/1/import/initial", json=request).status_code == 200
    cup = repository.one("SELECT * FROM tournaments WHERE id=1")
    assert (cup["arena_address"], cup["admin_revision"]) == ("Sörbyvallen, Örebro", 1)
    with imported_cups() as con:
        con.execute("UPDATE tournaments SET arena_address='Manuellt vald arena' WHERE id=1")
        con.commit()
    assert api.post("/api/admin/cups/1/import/initial", json=request).status_code == 200
    assert repository.one("SELECT arena_address FROM tournaments WHERE id=1")["arena_address"] == "Manuellt vald arena"
    assert repository.one("SELECT arena_address FROM tournaments WHERE id=2")["arena_address"] is None
    assert api.post("/api/admin/cups/2/import/initial", json=request).status_code == 404


def test_old_import_location_is_reused_publicly_without_mutating_or_crossing_cups(imported_cups):
    with imported_cups() as con:
        con.execute("INSERT INTO tournament_setup_imports(tournament_id,import_kind,payload_json) VALUES(1,'initial_setup',?)",
                    (json.dumps({"location": "Sörbyvallen"}),))
        con.commit()
    cup = repository.one("SELECT * FROM tournaments WHERE id=1")
    assert repository.with_imported_location(cup)["arena_address"] == "Sörbyvallen"
    assert repository._public_tournament_projection(cup)["arena_address"] == "Sörbyvallen"
    assert repository.with_imported_location({**cup, "arena_address": "Ny adress"})["arena_address"] == "Ny adress"
    assert repository.with_imported_location({"id": 2, "arena_address": None})["arena_address"] is None
    assert repository.one("SELECT arena_address FROM tournaments WHERE id=1")["arena_address"] is None


def test_publication_recognizes_location_from_old_import(imported_cups, monkeypatch):
    with imported_cups() as con:
        con.execute("INSERT INTO tournament_setup_imports(tournament_id,import_kind,payload_json) VALUES(1,'initial_setup',?)", (json.dumps({"location": "Sörbyvallen"}),))
        con.execute("INSERT INTO matches(tournament_id,scheduled_start) VALUES(1,'2026-10-24T10:00')")
        con.commit()
    monkeypatch.setattr(publish_reporting_repository, "_schedule_publication_analysis", lambda cup: {"conflicts": []})
    state = publish_reporting_repository._publication_payload(1)
    assert state["ready"] is True
    assert state["tournament"]["arena_address"] == "Sörbyvallen"
    assert publish_reporting_repository._publication_payload(2)["ready"] is False


@pytest.mark.parametrize("payload", [{}, {"location": None}, {"location": []}, {"venues": ["Plan 1", "Plan 2"]}, []])
def test_import_does_not_invent_an_address(imported_cups, payload):
    with imported_cups() as con:
        con.execute("INSERT INTO tournament_setup_imports(tournament_id,import_kind,payload_json) VALUES(1,'initial_setup',?)", (json.dumps(payload),))
        con.commit()
    assert repository.with_imported_location({"id": 1, "arena_address": None})["arena_address"] is None


def test_reviewed_playoffs_enable_playoff_mode_and_preserve_location(imported_cups):
    with imported_cups() as con:
        con.execute("UPDATE tournaments SET arena_address='Sörbyvallen' WHERE id=1")
        con.commit()
    result = playoff_import_repository.commit_playoff_import(7, 1, [{
        "label": "Final", "time": "14:00", "venue": "Sörbyvallen",
        "home_source": "ÖSK", "away_source": "AIK",
    }])
    assert result["imported"] == 1
    cup = repository.one("SELECT * FROM tournaments WHERE id=1")
    assert cup["arrangement_type"] == "tournament_playoffs"
    assert cup["arena_address"] == "Sörbyvallen"
    assert cup["admin_revision"] == 1
    match = repository.one("SELECT * FROM matches WHERE tournament_id=1")
    assert match["scheduled_start"] == "2026-10-24T14:00"
    with pytest.raises(ValueError, match="redan ett slutspelsträd"):
        playoff_import_repository.commit_playoff_import(7, 1, [{"label": "Final"}])
    assert repository.one("SELECT COUNT(*) AS n FROM matches")["n"] == 1


def test_bad_playoff_sources_roll_back_the_entire_import(imported_cups):
    with pytest.raises(ValueError, match="kan inte tolkas säkert"):
        playoff_import_repository.commit_playoff_import(7, 1, [{
            "label": "Final", "home_source": "Saknat lag", "away_source": "AIK", "time": "14:00",
        }])
    assert repository.one("SELECT COUNT(*) AS n FROM brackets")["n"] == 0
    assert repository.one("SELECT arrangement_type FROM tournaments WHERE id=1")["arrangement_type"] == "tournament"


def test_placement_groups_can_have_repeated_names_and_unknown_teams(imported_cups):
    with imported_cups() as con:
        con.executemany("INSERT INTO groups VALUES(?,1,?)", [(10,"A"),(11,"B"),(12,"C")])
        con.commit()
    rows = []
    for rank, name in [(1,"GULDGRUPPEN"),(2,"SILVERGRUPPEN"),(3,"BRONSGRUPPEN")]:
        for home, away in [("A","B"),("A","C"),("B","C")]:
            rows.append({"label": name, "time": f"{12+len(rows)//3}:{(len(rows)%3)*20:02d}",
                         "venue": "Sörbyvallen", "home_source": f"{rank}:a grupp {home}", "away_source": f"{rank}:a grupp {away}"})
    result = playoff_import_repository.commit_playoff_import(7,1,rows)
    assert result["imported"] == 9
    matches = repository.all_rows("SELECT * FROM matches ORDER BY match_no")
    assert [m["stage"] for m in matches] == [r["label"] for r in rows]
    assert matches[0]["home_source"] == "group:10:1"
    assert matches[-1]["away_source"] == "group:12:3"
    assert all(m["scheduled_start"] and m["pitch_number"] for m in matches)


def test_repeated_labels_cannot_make_a_winner_reference_ambiguous(imported_cups):
    rows = [{"label":"Semifinal", "time":time, "home_source":"ÖSK", "away_source":"AIK"} for time in ["10:00","11:00"]]
    rows.append({"label":"Final", "time":"12:00", "home_source":"Vinnare semifinal", "away_source":"AIK"})
    response = client().post("/api/admin/cups/1/import/playoffs",json={"playoff_matches":rows})
    assert response.status_code == 422
    assert "pekar på flera matcher" in response.json()["detail"]
    assert repository.one("SELECT COUNT(*) AS n FROM matches")["n"] == 0
    assert repository.one("SELECT COUNT(*) AS n FROM brackets")["n"] == 0


def test_duplicate_match_rows_are_still_rejected(imported_cups):
    row = {"label":"GULDGRUPPEN", "time":"12:00", "venue":"Sörbyvallen", "home_source":"ÖSK", "away_source":"AIK"}
    with pytest.raises(ValueError,match="dubblett"):
        playoff_import_repository.commit_playoff_import(7,1,[row,row])
    assert repository.one("SELECT COUNT(*) AS n FROM matches")["n"] == 0
