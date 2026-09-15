import sqlite3

import pytest

from cupnavi_api import schedule_admin_repository as repository


def _payload(start="2026-10-24T09:00"):
    return {
        "match_count": 1,
        "unscheduled_count": 0,
        "matches": [{"id": 1, "match_no": 1, "scheduled_start": start, "pitch_number": 1}],
        "conflict_analysis": {"error_count": 0},
    }


def _database(tmp_path):
    path = tmp_path / "confirm.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY,schedule_dirty INTEGER)")
    con.execute("INSERT INTO tournaments VALUES(1,1)")
    con.commit(); con.close()
    return path


def test_confirmation_clears_dirty_only_when_match_fits_confirmed_window(monkeypatch, tmp_path):
    path = _database(tmp_path)
    monkeypatch.setattr(repository, "admin_schedule", lambda *_: _payload())
    monkeypatch.setattr(repository, "one", lambda *_: {"halves": 1, "minutes_per_half": 30, "halftime_minutes": 0})
    monkeypatch.setattr(repository, "all_rows", lambda *_: [{"pitch_number": 1, "play_date": "2026-10-24", "start_time": "08:00", "end_time": "10:00"}])
    monkeypatch.setattr(repository, "connect", lambda: sqlite3.connect(path))

    result = repository.confirm_current_schedule(4, 1)

    assert result["match_count"] == 1
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT schedule_dirty FROM tournaments WHERE id=1").fetchone()[0] == 0


def test_confirmation_rejects_match_outside_confirmed_window(monkeypatch, tmp_path):
    path = _database(tmp_path)
    monkeypatch.setattr(repository, "admin_schedule", lambda *_: _payload("2026-10-24T09:45"))
    monkeypatch.setattr(repository, "one", lambda *_: {"halves": 1, "minutes_per_half": 30, "halftime_minutes": 0})
    monkeypatch.setattr(repository, "all_rows", lambda *_: [{"pitch_number": 1, "play_date": "2026-10-24", "start_time": "08:00", "end_time": "10:00"}])
    monkeypatch.setattr(repository, "connect", lambda: sqlite3.connect(path))

    with pytest.raises(ValueError, match="utanför planens bekräftade öppettid"):
        repository.confirm_current_schedule(4, 1)
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT schedule_dirty FROM tournaments WHERE id=1").fetchone()[0] == 1


def test_draft_preview_link_uses_authenticated_preview_route():
    source = (repository.__file__.replace("cupnavi_api/schedule_admin_repository.py", "frontend-next/src/components/publish-reporting-admin.tsx"))
    text = open(source, encoding="utf-8").read()
    assert "?preview=1&cup=${cupId}" in text
