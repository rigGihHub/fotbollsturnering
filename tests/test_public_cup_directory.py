"""Homepage directory privacy, date boundaries and public HTTP contract."""
import sqlite3
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from cupnavi_api import public_directory_repository as directory
from cupnavi_api.main import app


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "directory.db"
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE tournaments (
        id INTEGER PRIMARY KEY, name TEXT, public_slug TEXT, start_date TEXT, end_date TEXT,
        is_published INTEGER, lifecycle_status TEXT, arrangement_type TEXT, arena_address TEXT,
        owner_account_id INTEGER, feedback_email TEXT, reporter_code TEXT)""")
    yield con
    con.close()


def add(con, id, start, end=None, *, published=1, lifecycle="published", slug=None):
    con.execute("INSERT INTO tournaments VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (id, f"Cup {id}", slug, start, end, published, lifecycle, "matchcamp", "Testplan", 7, "private@example.org", "secret"))
    con.commit()


def test_only_published_non_trashed_arrangements_and_minimal_fields(database):
    add(database, 1, "2026-10-09", slug="cup-1")
    add(database, 2, "2026-10-09", published=0)
    add(database, 3, "2026-10-09", lifecycle="trashed")
    add(database, 4, "2026-10-09", lifecycle="purged")
    add(database, 5, "2026-10-09", lifecycle=None)
    payload = directory.public_cup_directory(today=date(2026, 10, 9))
    assert [cup["id"] for cup in payload["cups"]] == [1, 5]
    assert payload["as_of"] == "2026-10-09"
    assert set(payload["cups"][0]) == {"id", "name", "public_slug", "start_date", "end_date", "arrangement_type", "arena_address", "status"}
    assert "secret" not in str(payload) and "private@example.org" not in str(payload)


def test_dates_are_inclusive_and_completed_are_newest_first(database):
    for id, start, end in [(1, "2026-10-09", "2026-10-10"), (2, "2026-10-08", "2026-10-09"),
                           (3, "2026-10-10", None), (4, "2026-10-01", "2026-10-08"),
                           (5, "2026-09-01", "2026-09-03"), (6, "2026-10-12", None)]:
        add(database, id, start, end)
    cups = directory.public_cup_directory(today=date(2026, 10, 9))["cups"]
    assert [(cup["id"], cup["status"]) for cup in cups] == [(2, "ongoing"), (1, "ongoing"), (3, "upcoming"), (6, "upcoming"), (4, "completed"), (5, "completed")]


def test_invalid_or_missing_dates_remain_accessible_without_wrong_status(database):
    add(database, 1, "invalid")
    add(database, 2, None, "2026-10-09")
    add(database, 3, "2026-10-09", "2026-10-01")
    cups = {cup["id"]: cup for cup in directory.public_cup_directory(today=date(2026, 10, 9))["cups"]}
    assert cups[1]["status"] == "undated" and cups[1]["start_date"] is None
    assert cups[2]["status"] == cups[3]["status"] == "ongoing"
    assert cups[2]["start_date"] == cups[3]["end_date"] == "2026-10-09"


def test_current_day_uses_stockholm_timezone(database, monkeypatch):
    class FixedDatetime:
        @staticmethod
        def now(zone):
            return datetime(2026, 10, 8, 22, 30, tzinfo=timezone.utc).astimezone(zone)
    monkeypatch.setattr(directory, "datetime", FixedDatetime)
    add(database, 1, "2026-10-09")
    assert directory.public_cup_directory()["cups"][0]["status"] == "ongoing"


def test_public_endpoint_needs_no_login_and_is_not_cached(database):
    add(database, 1, "2026-10-09", slug="cup-1")
    response = TestClient(app).get("/api/public/cups")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["cups"][0]["public_slug"] == "cup-1"
    database.execute("UPDATE tournaments SET is_published=0")
    database.commit()
    assert TestClient(app).get("/api/public/cups").json()["cups"] == []


def test_older_schema_without_optional_directory_columns(database):
    database.execute("DROP TABLE tournaments")
    database.execute("CREATE TABLE tournaments (id INTEGER, name TEXT, public_slug TEXT, start_date TEXT, end_date TEXT, is_published INTEGER)")
    database.execute("INSERT INTO tournaments VALUES (1,'Older cup',NULL,'2026-10-09',NULL,1)")
    database.commit()
    cup = directory.public_cup_directory(today=date(2026, 10, 9))["cups"][0]
    assert cup["status"] == "ongoing" and cup["arrangement_type"] is None
