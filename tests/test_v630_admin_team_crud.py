import sqlite3
from pathlib import Path

import pytest

from cupnavi_api.admin_repository import (
    admin_teams,
    create_team,
    delete_team,
    update_team,
)


@pytest.fixture()
def team_database(tmp_path, monkeypatch):
    path = tmp_path / "cupnavi.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE tournament_members(
                tournament_id INTEGER NOT NULL,
                organizer_account_id INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE teams(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                group_id INTEGER,
                age_class TEXT,
                primary_color TEXT NOT NULL DEFAULT '#111827',
                secondary_color TEXT NOT NULL DEFAULT '#FFFFFF'
            );
            CREATE TABLE matches(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                home_source TEXT,
                away_source TEXT
            );
            INSERT INTO tournament_members VALUES(10,1,'owner');
            """
        )
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    return path


def test_team_crud_is_tournament_and_membership_scoped(team_database):
    created = create_team(1, 10, {"name": "  ÖSK P2014  ", "age_class": " P2014 "})
    assert created["name"] == "ÖSK P2014"
    assert created["primary_color"] == "#111827"
    assert admin_teams(2, 10) is None

    saved = update_team(
        1, 10, created["id"],
        {"name": "ÖSK P2014 Svart", "primary_color": "#123ABC", "secondary_color": "#ffffff"},
    )
    assert saved["name"] == "ÖSK P2014 Svart"
    assert saved["primary_color"] == "#123ABC"
    assert update_team(2, 10, created["id"], {"name": "Kapad"}) is None

    deleted = delete_team(1, 10, created["id"])
    assert deleted["name"] == "ÖSK P2014 Svart"
    assert admin_teams(1, 10) == []


def test_duplicate_names_and_invalid_colors_are_rejected(team_database):
    create_team(1, 10, {"name": "Karlslund"})
    with pytest.raises(ValueError, match="samma namn"):
        create_team(1, 10, {"name": "  KARLSLUND "})
    with pytest.raises(ValueError, match="#RRGGBB"):
        create_team(1, 10, {"name": "Adolfsberg", "primary_color": "black"})


def test_scheduled_team_cannot_be_deleted_silently(team_database):
    team = create_team(1, 10, {"name": "Forward"})
    with sqlite3.connect(team_database) as con:
        con.execute("INSERT INTO matches(tournament_id,home_source,away_source) VALUES(10,?,'team:999')", (f"team:{team['id']}",))
    with pytest.raises(ValueError, match="används i schemat"):
        delete_team(1, 10, team["id"])
    assert len(admin_teams(1, 10)) == 1


def test_v630_frontend_and_api_contracts_are_wired():
    root = Path(__file__).resolve().parents[1]
    api = (root / "cupnavi_api" / "main.py").read_text(encoding="utf-8")
    ui = (root / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    assert '@app.get("/api/admin/cups/{tournament_id}/teams")' in api
    assert '@app.post("/api/admin/cups/{tournament_id}/teams",status_code=201)' in api
    assert '@app.put("/api/admin/cups/{tournament_id}/teams/{team_id}")' in api
    assert '@app.delete("/api/admin/cups/{tournament_id}/teams/{team_id}")' in api
    assert 'id="teams"' in ui
    assert "Lägg till lag" in ui and "Redigera" in ui and "Ta bort" in ui
