from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import threading

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import cupnavi_api.role_access_routes as roles
from cupnavi_api.repository import connect


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(tmp_path / "reporter.db"))
    monkeypatch.setenv("CUPNAVI_SESSION_SECRET", "isolated-reporter-tests")
    monkeypatch.setattr(roles, "_has_tournament_access", lambda account, cup: account == 1)
    monkeypatch.setattr(roles, "_REPORTER_SCHEMA_READY", False)
    with connect() as con:
        con.executescript("""
            CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT,public_slug TEXT,lifecycle_status TEXT);
            INSERT INTO tournaments VALUES(1,'Cup A','cup-a','draft'),(2,'Cup B','cup-b','published');
            CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER);
            INSERT INTO matches VALUES(20,2);
            CREATE TABLE rate_limits(scope TEXT,subject_hash TEXT,window_start INTEGER,count INTEGER,last_seen INTEGER,
                                     PRIMARY KEY(scope,subject_hash,window_start));
            CREATE TABLE match_reporter_credentials(tournament_id INTEGER PRIMARY KEY,code_salt TEXT NOT NULL,
                       code_hash TEXT NOT NULL,created_at TEXT NOT NULL,rotated_at TEXT);
        """)
        con.commit()
    app = FastAPI()
    roles.register_role_access_routes(app, lambda _: {"id": 1})
    return TestClient(app)


def login(client, code, **kwargs):
    return client.post("/api/reporter/session", json={"code": code, **kwargs})


def legacy(cup, code, hours_ago=0, valid_hours=48):
    roles._ensure_reporter_table()
    issued = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    salt, digest = roles.new_code_hash(code)
    with connect() as con:
        con.execute("INSERT INTO match_reporter_credentials(tournament_id,code_salt,code_hash,created_at,rotated_at,valid_hours) VALUES(?,?,?,?,?,?)",
                    (cup, salt, digest, issued, issued, valid_hours))
        con.commit()


def test_code_only_login_finds_cup_and_preserves_leading_zeroes(client, monkeypatch):
    monkeypatch.setattr(roles, "generate_short_numeric_code", lambda _: "0042")
    result = roles.rotate_reporter_code(1, 2, 72)
    assert result["code"] == "0042" and result["active"]
    response = login(client, "0042")
    assert response.status_code == 200
    assert response.json()["cup"]["id"] == 2
    assert login(client, "0042", cup="cup-a").status_code == 401
    stored = roles._credential(2)
    assert stored["code_lookup"] != "0042" and stored["code_hash"] != "0042"


def test_login_can_return_reporting_payload_without_followup_requests(client, monkeypatch):
    monkeypatch.setattr(roles, "admin_reporting", lambda account, cup: {
        "matches": [{"id": 20, "home_team": "A", "away_team": "B"}],
        "settings": {"scorers": False},
    })
    code = roles.rotate_reporter_code(1, 2)["code"]
    response = login(client, code, include_reporting=True)
    assert response.status_code == 200
    assert response.json()["cup"]["id"] == 2
    assert response.json()["matches"][0]["id"] == 20
    assert response.json()["settings"]["scorers"] is False


def test_late_login_does_not_restart_72_hour_deadline(client, monkeypatch):
    result = roles.rotate_reporter_code(1, 1, 168)
    assert result["valid_hours"] == 72
    deadline = roles._credential_expiry(roles._credential(1))
    monkeypatch.setattr(roles, "time", SimpleNamespace(time=lambda: deadline - 1))
    token = login(client, result["code"]).json()["token"]
    assert roles._verify_reporter_session(token)["exp"] == deadline
    monkeypatch.setattr(roles, "time", SimpleNamespace(time=lambda: deadline))
    assert login(client, result["code"]).status_code == 401
    assert roles._verify_reporter_session(token) is None
    assert roles.reporter_code_status(1, 1)["active"] is False


def test_shorter_code_lifetime_and_rotation_revoke_existing_sessions(client, monkeypatch):
    codes = iter(["1111", "1111", "2222"])
    monkeypatch.setattr(roles, "generate_short_numeric_code", lambda _: next(codes))
    first = roles.rotate_reporter_code(1, 1, 8)
    token = login(client, first["code"]).json()["token"]
    row = roles._credential(1)
    assert roles._credential_expiry(row) - int(datetime.fromisoformat(row["rotated_at"]).timestamp()) == 8 * 3600
    second = roles.rotate_reporter_code(1, 1, 24)
    assert second["code"] == "2222"
    assert roles._verify_reporter_session(token) is None
    assert login(client, first["code"]).status_code == 401
    assert login(client, second["code"]).status_code == 200


def test_extension_never_pushes_code_beyond_three_days_from_now(client):
    result = roles.rotate_reporter_code(1, 1, 72)
    response = client.post(
        "/api/admin/cups/1/role-codes/reporter/extend",
        json={"additional_hours": 72},
    )
    assert response.status_code == 200
    deadline = datetime.fromisoformat(response.json()["expires_at"]).timestamp()
    assert deadline <= datetime.now(timezone.utc).timestamp() + roles.MAX_REPORTER_SESSION_SECONDS + 2
    assert login(client, result["code"]).status_code == 200


def test_finished_match_is_locked_for_reporter_but_not_admin_result_api(monkeypatch):
    monkeypatch.setattr(roles, "_require_reporter_match", lambda *_: {"match_status": "finished"})
    with pytest.raises(HTTPException, match="Endast administratören") as error:
        roles._require_reporter_editable_match(1, 20)
    assert error.value.status_code == 409

    routes = Path("cupnavi_api/publish_reporting_routes.py").read_text(encoding="utf-8")
    assert "_require_reporter_editable_match" not in routes
    assert "r=save_result(" in routes


def test_duplicate_legacy_codes_never_choose_first_cup(client):
    legacy(1, "1234")
    assert login(client, "1234").json()["cup"]["id"] == 1
    legacy(2, "1234")
    assert login(client, "1234").status_code == 401
    assert login(client, "1234", cup="cup-a").status_code == 401


def test_generation_avoids_active_legacy_collision(client, monkeypatch):
    legacy(1, "1234")
    codes = iter(["1234", "5678"])
    monkeypatch.setattr(roles, "generate_short_numeric_code", lambda _: next(codes))
    assert roles.rotate_reporter_code(1, 2)["code"] == "5678"


def test_old_seven_day_codes_expire_after_three_days(client):
    legacy(1, "9999", hours_ago=73, valid_hours=168)
    assert login(client, "9999").status_code == 401
    assert roles.reporter_code_status(1, 1)["active"] is False


def test_expired_code_reservation_can_be_reused(client, monkeypatch):
    monkeypatch.setattr(roles, "generate_short_numeric_code", lambda _: "1234")
    roles.rotate_reporter_code(1, 1)
    with connect() as con:
        expired = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        con.execute("UPDATE match_reporter_credentials SET rotated_at=?,expires_at=? WHERE tournament_id=1",
                    (expired, expired))
        con.commit()
    assert roles.rotate_reporter_code(1, 2)["code"] == "1234"
    assert login(client, "1234").json()["cup"]["id"] == 2


def test_parallel_allocations_cannot_share_active_code(client, monkeypatch):
    roles._ensure_reporter_table()
    local = threading.local()
    def candidate(_):
        local.count = getattr(local, "count", 0) + 1
        return "1234" if local.count == 1 else "5678"
    monkeypatch.setattr(roles, "generate_short_numeric_code", candidate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda cup: roles.rotate_reporter_code(1, cup), [1, 2]))
    assert {r["code"] for r in results} == {"1234", "5678"}


def test_rate_limit_cannot_be_reset_by_changing_cup_or_code(client):
    for attempt in range(10):
        assert login(client, f"{attempt:04d}", cup=str(attempt)).status_code == 401
    response = login(client, "4321", cup="different-cup")
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0


@pytest.mark.parametrize("code", ["123", "12345", "12a4", "１２３４", " 1234", ""])
def test_only_exactly_four_ascii_digits_are_accepted(client, code):
    assert login(client, code).status_code == 401


def test_session_cannot_write_other_cup_or_access_trashed_cup(client):
    code = roles.rotate_reporter_code(1, 1)["code"]
    token = login(client, code).json()["token"]
    headers = {"Authorization": "Bearer " + token}
    response = client.put("/api/reporter/reporting/matches/20", headers=headers, json={"home_score": 1, "away_score": 0})
    assert response.status_code == 404
    with connect() as con:
        con.execute("UPDATE tournaments SET lifecycle_status='trashed' WHERE id=1")
        con.commit()
    assert login(client, code).status_code == 401
    assert client.get("/api/reporter/session", headers=headers).status_code == 401
