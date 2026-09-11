import sqlite3

import pytest

from cupnavi_api.group_admin_repository import (
    admin_groups,
    assign_team_group,
    create_group,
    delete_group,
    update_group,
)
from cupnavi_api.main import app


def _schema(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE tournament_members (
            organizer_account_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL
        );
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age_class TEXT
        );
        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            group_id INTEGER,
            age_class TEXT,
            primary_color TEXT,
            secondary_color TEXT
        );
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            group_id INTEGER,
            home_source TEXT,
            away_source TEXT
        );
        INSERT INTO tournament_members(organizer_account_id,tournament_id) VALUES(1,10);
        INSERT INTO teams(tournament_id,name,age_class,primary_color,secondary_color)
        VALUES(10,'ÖSK P2014','P2014','#111827','#FFFFFF');
        """
    )
    con.commit()
    con.close()


def test_group_crud_and_team_assignment(monkeypatch, tmp_path):
    database = tmp_path / "v631.sqlite"
    _schema(database)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(database))

    created = create_group(1, 10, {"name": "Grupp A", "age_class": "P2014"})
    assert created["name"] == "Grupp A"
    assert created["team_count"] == 0

    updated = update_group(1, 10, created["id"], {"name": "Grupp Alpha"})
    assert updated["name"] == "Grupp Alpha"

    team = assign_team_group(1, 10, 1, created["id"])
    assert team["group_id"] == created["id"]
    assert admin_groups(1, 10)[0]["team_count"] == 1

    with pytest.raises(ValueError, match="innehåller lag"):
        delete_group(1, 10, created["id"])

    unassigned = assign_team_group(1, 10, 1, None)
    assert unassigned["group_id"] is None
    deleted = delete_group(1, 10, created["id"])
    assert deleted["name"] == "Grupp Alpha"
    assert admin_groups(1, 10) == []


def test_group_routes_are_exposed():
    routes = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    assert ("/api/admin/cups/{tournament_id}/groups", "GET") in routes
    assert ("/api/admin/cups/{tournament_id}/groups", "POST") in routes
    assert ("/api/admin/cups/{tournament_id}/groups/{group_id}", "PUT") in routes
    assert ("/api/admin/cups/{tournament_id}/groups/{group_id}", "DELETE") in routes
    assert ("/api/admin/cups/{tournament_id}/teams/{team_id}/group", "PUT") in routes
