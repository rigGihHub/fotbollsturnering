import sqlite3

import pytest

from cupnavi_api.access_repository import (
    add_tournament_member,
    change_password,
    remove_tournament_member,
    tournament_activity,
    tournament_members,
    update_tournament_member_role,
)
from cupnavi_api.admin_auth import issue_session, password_hash, verify_session
from cupnavi_api.admin_repository import (
    ConcurrentUpdateError,
    admin_cupinfo,
    organizer_account,
    organizer_tournaments,
    purge_trashed_tournaments,
    restore_tournament,
    trash_tournament,
    trashed_tournaments,
    update_cupinfo,
)
from cupnavi_api.cup_create_repository import create_owner_tournament
from cupnavi_api.publish_reporting_repository import admin_publication, set_publication
from cupnavi_core.migrations import ensure_v37_schema_compat


@pytest.fixture()
def multiuser_database(tmp_path, monkeypatch):
    path = tmp_path / "multiuser.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE organizer_accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL UNIQUE,display_name TEXT,
                password_salt TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                disabled_at TEXT
            );
            CREATE TABLE tournaments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,public_slug TEXT UNIQUE,
                start_date TEXT,end_date TEXT,organizer TEXT,arena_address TEXT,organizer_phone TEXT,
                feedback_email TEXT,public_information TEXT,arrangement_type TEXT DEFAULT 'tournament',
                is_published INTEGER DEFAULT 0,lifecycle_status TEXT DEFAULT 'draft',trashed_at TEXT
            );
            CREATE TABLE tournament_members(
                tournament_id INTEGER NOT NULL,organizer_account_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'owner',created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(tournament_id,organizer_account_id)
            );
            """
        )
        ensure_v37_schema_compat(con)
        for email, password in (("owner@example.se", "owner-password"), ("other@example.se", "other-password")):
            salt = "11" * 16 if email.startswith("owner") else "22" * 16
            con.execute(
                "INSERT INTO organizer_accounts(email,password_salt,password_hash) VALUES(?,?,?)",
                (email, salt, password_hash(password, salt)),
            )
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    monkeypatch.setenv("CUPNAVI_SESSION_SECRET", "multiuser-test-secret")
    return path


def test_regular_organizer_creates_owned_isolated_cup(multiuser_database):
    cup = create_owner_tournament(1, {"name": "Min föreningscup"})
    assert cup["role"] == "owner"
    assert [row["id"] for row in organizer_tournaments(1)] == [cup["id"]]
    assert organizer_tournaments(2) == []
    assert admin_cupinfo(2, cup["id"]) is None


def test_owner_manages_members_but_admin_cannot(multiuser_database):
    cup = create_owner_tournament(1, {"name": "Delad cup"})
    owner = {"id": 1, "email": "owner@example.se"}
    result = add_tournament_member(owner, cup["id"], {"email": "other@example.se", "role": "admin"})
    assert result["temporary_password"] is None
    assert {row["email"]: row["role"] for row in tournament_members(1, cup["id"])} == {
        "owner@example.se": "owner",
        "other@example.se": "admin",
    }
    with pytest.raises(PermissionError):
        add_tournament_member({"id": 2, "email": "other@example.se"}, cup["id"], {"email": "third@example.se"})
    with pytest.raises(ValueError, match="egen åtkomst"):
        remove_tournament_member(owner, cup["id"], 1)
    with pytest.raises(ValueError, match="minst en ägare"):
        update_tournament_member_role(owner, cup["id"], 1, "admin")


def test_cupinfo_rejects_stale_parallel_update_and_records_actor(multiuser_database):
    cup = create_owner_tournament(1, {"name": "Samtidig cup"})
    first = admin_cupinfo(1, cup["id"])
    saved = update_cupinfo(1, cup["id"], {"name": "Ny titel", "expected_revision": first["admin_revision"]})
    assert saved["admin_revision"] == first["admin_revision"] + 1
    with pytest.raises(ConcurrentUpdateError):
        update_cupinfo(1, cup["id"], {"name": "Gammal titel", "expected_revision": first["admin_revision"]})
    assert admin_cupinfo(1, cup["id"])["name"] == "Ny titel"
    assert any(item["summary"] == "Cupinformationen uppdaterades" for item in tournament_activity(1, cup["id"]))


def test_password_change_increments_session_version(multiuser_database):
    before = organizer_account(1)
    old_token = issue_session(before)
    assert verify_session(old_token)["sv"] == 1
    change_password(1, "owner-password", "a-new-secure-password")
    after = organizer_account(1)
    assert after["session_version"] == 2
    assert verify_session(old_token)["sv"] != after["session_version"]


def test_each_owner_has_an_isolated_trash_lifecycle(multiuser_database):
    owner_cup = create_owner_tournament(1, {"name": "Ägarens cup"})
    other_cup = create_owner_tournament(2, {"name": "Andras cup"})

    trash_tournament(1, owner_cup["id"], owner_cup["name"])
    trash_tournament(2, other_cup["id"], other_cup["name"])

    assert [cup["id"] for cup in trashed_tournaments(1)] == [owner_cup["id"]]
    assert [cup["id"] for cup in trashed_tournaments(2)] == [other_cup["id"]]
    with pytest.raises(PermissionError):
        restore_tournament(1, other_cup["id"])

    assert purge_trashed_tournaments(1) == 1
    assert trashed_tournaments(1) == []
    assert [cup["id"] for cup in trashed_tournaments(2)] == [other_cup["id"]]
    assert restore_tournament(2, other_cup["id"])["id"] == other_cup["id"]


def test_cross_account_ids_cannot_read_edit_publish_or_delete(multiuser_database):
    owner_cup = create_owner_tournament(1, {"name": "Privat cup"})
    cup_id = owner_cup["id"]

    assert admin_cupinfo(2, cup_id) is None
    assert update_cupinfo(2, cup_id, {"name": "Kapad cup"}) is None
    assert admin_publication(2, cup_id) is None
    assert set_publication(2, cup_id, False) is None
    with pytest.raises(PermissionError, match="cupens ägare"):
        trash_tournament(2, cup_id, owner_cup["name"])

    current = admin_cupinfo(1, cup_id)
    assert current["name"] == "Privat cup"
    assert current["is_published"] == 0


def test_admin_can_edit_and_unpublish_but_cannot_manage_ownership(multiuser_database):
    cup = create_owner_tournament(1, {"name": "Delad drift"})
    owner = {"id": 1, "email": "owner@example.se"}
    add_tournament_member(owner, cup["id"], {"email": "other@example.se", "role": "admin"})

    edited = update_cupinfo(2, cup["id"], {"name": "Delad drift 2"})
    assert edited["name"] == "Delad drift 2"
    with pytest.raises(PermissionError):
        trash_tournament(2, cup["id"], "Delad drift 2")
    with pytest.raises(PermissionError):
        add_tournament_member({"id": 2, "email": "other@example.se"}, cup["id"], {"email": "third@example.se"})
