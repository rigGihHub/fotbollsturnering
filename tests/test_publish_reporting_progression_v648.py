from types import SimpleNamespace

import pytest

import cupnavi_api.publish_reporting_repository as repo


class _Resolver:
    def resolve(self, source):
        mapping = {
            "team:1": SimpleNamespace(resolved=True, team_id=1, team_name="A"),
            "team:2": SimpleNamespace(resolved=True, team_id=2, team_name="B"),
            "winner:10": SimpleNamespace(resolved=True, team_id=1, team_name="A"),
            "team:3": SimpleNamespace(resolved=True, team_id=3, team_name="C"),
        }
        return mapping.get(source, SimpleNamespace(resolved=False, team_id=None, team_name=None))


def _semi(**updates):
    row = {
        "id": 10,
        "tournament_id": 7,
        "stage": "Semifinal",
        "home_source": "team:1",
        "away_source": "team:2",
        "home_score": 1,
        "away_score": 0,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
        "match_status": "finished",
    }
    row.update(updates)
    return row


def _final(**updates):
    row = {
        "id": 11,
        "tournament_id": 7,
        "stage": "Final",
        "home_source": "winner:10",
        "away_source": "team:3",
        "home_score": None,
        "away_score": None,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
        "match_status": "not_started",
    }
    row.update(updates)
    return row


def test_upstream_winner_cannot_change_after_dependent_final_has_result(monkeypatch):
    semifinal = _semi()
    final = _final(home_score=2, away_score=1, match_status="finished")
    monkeypatch.setattr(repo, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(repo, "one", lambda *_args, **_kwargs: dict(semifinal))
    monkeypatch.setattr(repo, "all_rows", lambda sql, *_args: [dict(semifinal), dict(final)] if "FROM matches" in sql else [])
    monkeypatch.setattr(repo, "_resolver_for_tournament", lambda *_: _Resolver())
    monkeypatch.setattr(repo, "_event_counts", lambda *_: {})

    with pytest.raises(RuntimeError, match="senare slutspelsmatch"):
        repo.save_result(1, 7, 10, 0, 1, 1, 0)


def test_safe_correction_before_final_starts_writes_new_result(monkeypatch):
    semifinal = _semi()
    final = _final()
    state = {"updated": None}

    class Conn:
        def execute(self, sql, params):
            if "UPDATE matches" in sql:
                state["updated"] = params
        def commit(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False

    calls = {"one": 0}
    def fake_one(sql, *_args):
        calls["one"] += 1
        if calls["one"] == 1:
            return dict(semifinal)
        return {
            "id": 10,
            "stage": "Semifinal",
            "home_source": "team:1",
            "away_source": "team:2",
            "home_score": 1,
            "away_score": 1,
            "home_penalties": 3,
            "away_penalties": 5,
            "decided_winner_id": None,
        }

    monkeypatch.setattr(repo, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(repo, "one", fake_one)
    monkeypatch.setattr(repo, "all_rows", lambda sql, *_args: [dict(semifinal), dict(final)] if "FROM matches" in sql else [])
    monkeypatch.setattr(repo, "_resolver_for_tournament", lambda *_: _Resolver())
    monkeypatch.setattr(repo, "_event_counts", lambda *_: {})
    monkeypatch.setattr(repo, "connect", lambda: Conn())

    result = repo.save_result(
        1, 7, 10, 1, 1, 1, 0,
        home_penalties=3,
        away_penalties=5,
    )
    assert state["updated"][:5] == (1, 1, 3, 5, None)
    assert result["outcome_resolved"] is True
    assert result["winner_side"] == "away"
    assert result["winner_team_id"] == 2


def test_reporting_marks_unresolved_tied_playoff_as_awaiting_decision(monkeypatch):
    tied = _semi(home_score=1, away_score=1)
    monkeypatch.setattr(repo, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(repo, "all_rows", lambda sql, *_args: [dict(tied)] if "FROM matches" in sql else [{"id":1,"name":"A"},{"id":2,"name":"B"}])
    monkeypatch.setattr(repo, "_resolver_for_tournament", lambda *_: _Resolver())
    payload = repo.admin_reporting(1, 7)
    assert payload["matches"][0]["status"] == "awaiting_decision"
    assert payload["matches"][0]["home_team"] == "A"
    assert payload["matches"][0]["away_team"] == "B"
