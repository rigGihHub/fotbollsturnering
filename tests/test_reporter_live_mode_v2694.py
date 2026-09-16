from pathlib import Path

import pytest

import cupnavi_api.publish_reporting_repository as reporting


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_reporter_status_transition_uses_compare_and_swap(monkeypatch):
    original = {
        "id": 10,
        "tournament_id": 7,
        "match_status": "not_started",
        "home_score": None,
        "away_score": None,
        "actual_started_at": None,
        "actual_finished_at": None,
    }
    updated = {**original, "match_status": "live", "actual_started_at": "2026-09-16T12:00:00"}
    calls = {"one": 0, "params": None}

    class Cursor:
        rowcount = 1

    class Conn:
        def execute(self, _sql, params):
            calls["params"] = params
            return Cursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_one(*_args, **_kwargs):
        calls["one"] += 1
        return dict(original if calls["one"] == 1 else updated)

    monkeypatch.setattr(reporting, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(reporting, "one", fake_one)
    monkeypatch.setattr(reporting, "connect", lambda: Conn())

    result = reporting.set_reporter_match_status(1, 7, 10, "live", "not_started")
    assert result["match_status"] == "live"
    assert calls["params"][0] == "live"
    assert calls["params"][-1] == "not_started"


def test_reporter_cannot_finish_without_a_saved_result(monkeypatch):
    row = {
        "id": 10,
        "tournament_id": 7,
        "match_status": "live",
        "home_score": None,
        "away_score": None,
        "actual_started_at": "2026-09-16T12:00:00",
        "actual_finished_at": None,
    }
    monkeypatch.setattr(reporting, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(reporting, "one", lambda *_args, **_kwargs: dict(row))
    with pytest.raises(ValueError, match="slutresultatet"):
        reporting.set_reporter_match_status(1, 7, 10, "finished", "live")


def test_reporter_cannot_skip_or_reopen_lifecycle(monkeypatch):
    row = {
        "id": 10,
        "tournament_id": 7,
        "match_status": "not_started",
        "home_score": 1,
        "away_score": 0,
        "actual_started_at": None,
        "actual_finished_at": None,
    }
    monkeypatch.setattr(reporting, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(reporting, "one", lambda *_args, **_kwargs: dict(row))
    with pytest.raises(ValueError, match="inte tillåten"):
        reporting.set_reporter_match_status(1, 7, 10, "finished", "not_started")


def test_live_score_controls_are_large_optimistic_and_offline_safe():
    reporter = read("frontend-next/src/components/reporter-client.tsx")
    queue = read("frontend-next/src/lib/reporter-offline.ts")
    css = read("frontend-next/src/app/reporter-flow-v2667.css")
    assert "ReporterLiveControl" in reporter
    assert "Öka mål för" in reporter and "Minska mål för" in reporter
    assert "Starta match" in reporter and "Paus / halvtid" in reporter and "Avsluta match" in reporter
    assert "appendReporterMutation" in reporter
    assert "completeReporterResultMutation" in queue
    assert "Behåll serverbaslinjen" in queue
    assert ".reporter-live__team button{min-height:72px" in css


def test_public_match_status_comes_from_explicit_lifecycle_not_clock_guess():
    formatting = read("frontend-next/src/lib/format.ts")
    card = read("frontend-next/src/components/MatchCard.tsx")
    repository = read("cupnavi_api/repository.py")
    assert 'match.match_status === "live"' in formatting
    assert 'match.match_status === "halftime"' in formatting
    assert "Date.now()" not in formatting
    assert 'status === "halftime" ? "PAUS"' in card
    assert "match_status,status_updated_at" in repository
