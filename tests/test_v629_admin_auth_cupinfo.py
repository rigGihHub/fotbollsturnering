import sqlite3

import pytest

from cupnavi_api.admin_auth import issue_session, password_hash, verify_session
from cupnavi_api.admin_repository import (
    admin_cupinfo,
    authenticate_organizer,
    organizer_tournaments,
    update_cupinfo,
)


def _database(path):
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE organizer_accounts(
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                display_name TEXT,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                disabled_at TEXT
            );
            CREATE TABLE tournaments(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                public_slug TEXT,
                start_date TEXT,
                end_date TEXT,
                organizer TEXT,
                arena_address TEXT,
                organizer_phone TEXT,
                feedback_email TEXT,
                public_information TEXT,
                is_published INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE tournament_members(
                tournament_id INTEGER NOT NULL,
                organizer_account_id INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            """
        )
        salt = "11" * 16
        con.execute(
            "INSERT INTO organizer_accounts VALUES (1,?,?,?,?,NULL)",
            ("owner@example.se", "Cupägare", salt, password_hash("rätt lösenord", salt)),
        )
        con.execute(
            "INSERT INTO organizer_accounts VALUES (2,?,?,?,?,NULL)",
            ("other@example.se", "Annan", salt, password_hash("annat lösenord", salt)),
        )
        con.execute(
            "INSERT INTO tournaments(id,name,public_slug,is_published) VALUES (10,'Testcup','testcup',1)"
        )
        con.execute("INSERT INTO tournament_members VALUES (10,1,'owner')")


@pytest.fixture()
def admin_database(tmp_path, monkeypatch):
    path = tmp_path / "cupnavi.sqlite"
    _database(path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    return path


def test_session_is_signed_normalized_and_rejects_tampering(monkeypatch):
    monkeypatch.setenv("CUPNAVI_SESSION_SECRET", "test-secret")
    token = issue_session({"id": 7, "email": " Owner@Example.SE "})
    payload = verify_session(token)
    assert payload and payload["sub"] == 7
    assert payload["email"] == "owner@example.se"
    body, signature = token.split(".", 1)
    replacement = "A" if signature[-1] != "A" else "B"
    assert verify_session(f"{body}.{signature[:-1]}{replacement}") is None


def test_login_and_cup_list_are_membership_scoped(admin_database):
    account = authenticate_organizer(" OWNER@example.se ", "rätt lösenord")
    assert account == {"id": 1, "email": "owner@example.se", "display_name": "Cupägare"}
    assert authenticate_organizer("owner@example.se", "fel") is None
    assert [cup["id"] for cup in organizer_tournaments(1)] == [10]
    assert organizer_tournaments(2) == []


def test_cupinfo_update_is_whitelisted_and_requires_membership(admin_database):
    saved = update_cupinfo(
        1,
        10,
        {
            "name": "  Nytt cupnamn  ",
            "organizer_phone": " 070-123 45 67 ",
            "is_published": 0,
            "unknown_field": "ignoreras",
        },
    )
    assert saved["name"] == "Nytt cupnamn"
    assert saved["organizer_phone"] == "070-123 45 67"
    assert saved["is_published"] == 1
    assert admin_cupinfo(2, 10) is None
    assert update_cupinfo(2, 10, {"name": "Kapad cup"}) is None

    with sqlite3.connect(admin_database) as con:
        assert con.execute("SELECT name FROM tournaments WHERE id=10").fetchone()[0] == "Nytt cupnamn"


def test_cupinfo_rejects_blank_name(admin_database):
    with pytest.raises(ValueError, match="Cupnamn krävs"):
        update_cupinfo(1, 10, {"name": "   "})
