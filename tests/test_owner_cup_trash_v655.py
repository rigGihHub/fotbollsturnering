import sqlite3
from pathlib import Path

import pytest

from cupnavi_api.admin_repository import admin_cupinfo, organizer_tournaments, trash_tournament


@pytest.fixture()
def cup_database(tmp_path, monkeypatch):
    path = tmp_path / "cupnavi.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE tournaments(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                public_slug TEXT,
                start_date TEXT,
                end_date TEXT,
                is_published INTEGER NOT NULL DEFAULT 0,
                lifecycle_status TEXT NOT NULL DEFAULT 'draft',
                trashed_at TEXT
            );
            CREATE TABLE tournament_members(
                tournament_id INTEGER NOT NULL,
                organizer_account_id INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            INSERT INTO tournaments(id,name,public_slug,is_published) VALUES(10,'Örebro Cupen','orebro-cupen',1);
            INSERT INTO tournaments(id,name,public_slug,is_published) VALUES(11,'Nästa Cup','nasta-cup',0);
            INSERT INTO tournament_members VALUES(10,1,'owner');
            """
        )
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    return path


def test_owner_moves_cup_to_recoverable_trash(cup_database):
    removed = trash_tournament(0, 10, "Örebro Cupen")
    assert removed["name"] == "Örebro Cupen"
    with sqlite3.connect(cup_database) as con:
        row = con.execute("SELECT lifecycle_status,trashed_at,is_published FROM tournaments WHERE id=10").fetchone()
    assert row[0] == "trashed"
    assert row[1]
    assert row[2] == 0
    assert [cup["id"] for cup in organizer_tournaments(0)] == [11]
    assert admin_cupinfo(0, 10) is None


def test_wrong_name_and_non_member_cannot_remove_cup(cup_database):
    with pytest.raises(ValueError, match="stämmer inte"):
        trash_tournament(0, 10, "Fel cup")
    with pytest.raises(PermissionError, match="cupens ägare"):
        trash_tournament(2, 10, "Örebro Cupen")
    assert [cup["id"] for cup in organizer_tournaments(0)] == [11, 10]


def test_v655_cup_owner_ui_and_api_contract():
    root = Path(__file__).resolve().parents[1]
    api = (root / "cupnavi_api/main.py").read_text(encoding="utf-8")
    ui = (root / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
    assert '@app.delete("/api/admin/cups/{tournament_id}")' in api
    assert 'const isOwner = account.role === "owner" || account.is_owner === true;' in ui
    assert 'const canManageCup = isOwner || activeCup?.role === "owner";' in ui
    assert "activeCup&&canManageCup" in ui
    assert "Ta bort cup" in ui
    assert "confirmed_name" in ui
    assert "flyttats till papperskorgen" in ui


def test_v655_release_contract_survives_later_releases():
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION.txt").read_text(encoding="utf-8").strip()
    parts = version.split("-", 2)
    assert len(parts) == 3
    assert int(parts[1]) >= 655
    assert f'APP_VERSION = "{version}"' in (root / "cupnavi_core/version.py").read_text(encoding="utf-8")
