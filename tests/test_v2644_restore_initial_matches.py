import json
from datetime import date

import cupnavi_api.import_summary_repository as repository


def test_restore_requires_an_empty_schedule(monkeypatch):
    monkeypatch.setattr(repository, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(repository, "_count", lambda *_: 1)
    try:
        repository.restore_initial_matches(1, 9)
    except ValueError as exc:
        assert "redan matcher" in str(exc)
    else:
        raise AssertionError("Restoring over an existing schedule must fail")


def test_restore_reuses_saved_initial_payload(monkeypatch):
    payload = {"matches": [{"home_team": "A", "away_team": "B", "time": "09:00", "venue": "Plan 1"}]}
    rows = iter([{"payload_json": json.dumps(payload)}, {"start_date": "2026-10-24"}])
    monkeypatch.setattr(repository, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(repository, "_count", lambda *_: 0)
    monkeypatch.setattr(repository, "one", lambda *_: next(rows))
    captured = {}
    def apply(connect, tournament_id, restored_payload, fallback):
        captured.update(tournament_id=tournament_id, payload=restored_payload, fallback=fallback)
        return 12, False
    monkeypatch.setattr(repository, "apply_document_matches_idempotent", apply)
    result = repository.restore_initial_matches(1, 9)
    assert result["restored_count"] == 12
    assert captured == {"tournament_id": 9, "payload": payload, "fallback": date(2026, 10, 24)}
