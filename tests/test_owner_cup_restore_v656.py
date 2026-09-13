import sqlite3
from pathlib import Path

import pytest

from cupnavi_api.admin_repository import (
    organizer_tournaments,
    restore_tournament,
    trashed_tournaments,
    trash_tournament,
)


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
            """
        )
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    return path


def test_owner_can_list_and_restore_trashed_cup(cup_database):
    trash_tournament(0, 10, "Örebro Cupen")
    trash = trashed_tournaments(0)
    assert [cup["id"] for cup in trash] == [10]
    assert trash[0]["trashed_at"]

    restored = restore_tournament(0, 10)
    assert restored["id"] == 10
    assert restored["is_published"] == 0
    assert restored["trashed_at"] is None

    assert trashed_tournaments(0) == []
    assert [cup["id"] for cup in organizer_tournaments(0)] == [11, 10]
    with sqlite3.connect(cup_database) as con:
        row = con.execute(
            "SELECT lifecycle_status,trashed_at,is_published FROM tournaments WHERE id=10"
        ).fetchone()
    assert row == ("draft", None, 0)


def test_non_owner_cannot_read_or_restore_trash(cup_database):
    trash_tournament(0, 10, "Örebro Cupen")
    with pytest.raises(PermissionError, match="CupNavi-ägaren"):
        trashed_tournaments(1)
    with pytest.raises(PermissionError, match="CupNavi-ägaren"):
        restore_tournament(1, 10)


def test_restore_only_accepts_cups_that_are_in_trash(cup_database):
    assert restore_tournament(0, 10) is None


def test_v656_api_contract_survives_later_releases():
    root = Path(__file__).resolve().parents[1]
    api = (root / "cupnavi_api/main.py").read_text(encoding="utf-8")
    assert '@app.get("/api/admin/trash")' in api
    assert '@app.post("/api/admin/trash/{tournament_id}/restore")' in api
    version = (root / "VERSION.txt").read_text(encoding="utf-8").strip()
    parts = version.split("-", 2)
    assert len(parts) == 3
    assert int(parts[1]) >= 656
    assert f'APP_VERSION = "{version}"' in (root / "cupnavi_core/version.py").read_text(encoding="utf-8")
