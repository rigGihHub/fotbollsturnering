from cupnavi_api import publish_reporting_repository as reporting
from cupnavi_api.repository import _public_tournament_projection


def test_public_projection_exposes_arrangement_semantics():
    projected = _public_tournament_projection({
        "id": 7,
        "name": "Höstcamp",
        "arrangement_type": "matchcamp",
        "results_counted": 0,
        "private_note": "never public",
    })
    assert projected["arrangement_type"] == "matchcamp"
    assert projected["results_counted"] == 0
    assert "private_note" not in projected


def test_matchcamp_draw_does_not_require_winner():
    assert reporting._match_requires_winner({"stage": "Matchcamp", "bracket_id": None}) is False
    assert reporting._match_requires_winner({"stage": "Final", "bracket_id": None}) is True
    assert reporting._match_requires_winner({"stage": "Egen rubrik", "bracket_id": 4}) is True


def test_matchcamp_never_uses_stale_playoff_configuration():
    assert reporting._uses_playoffs({
        "arrangement_type": "matchcamp",
        "playoff_format": "Slutspel – bara ettor och tvåor",
    }) is False
    assert reporting._uses_playoffs({"arrangement_type": "tournament"}) is False
    assert reporting._uses_playoffs({"arrangement_type": "tournament_playoffs"}) is True


def test_reporting_accepts_drawn_matchcamp_match(monkeypatch):
    match = {
        "id": 1,
        "stage": "Matchcamp",
        "bracket_id": None,
        "home_source": "team:10",
        "away_source": "team:11",
        "home_score": 2,
        "away_score": 2,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
    }
    monkeypatch.setattr(reporting, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(reporting, "_resolver_for_tournament", lambda *_: None)
    monkeypatch.setattr(
        reporting,
        "all_rows",
        lambda sql, *_: [dict(match)] if "FROM matches" in sql else [
            {"id": 10, "name": "Hemma"}, {"id": 11, "name": "Borta"}
        ],
    )
    result = reporting.admin_reporting(1, 7)
    assert result["matches"][0]["status"] == "played"


def test_matchcamp_publication_skips_bracket_validation(monkeypatch):
    tournament = {
        "id": 7,
        "arena_address": "Planen",
        "arrangement_type": "matchcamp",
        "playoff_format": "Slutspel – gammalt värde",
        "playoff_model_confirmed": 0,
        "schedule_dirty": 0,
    }
    monkeypatch.setattr(
        reporting,
        "one",
        lambda sql, *_: tournament if "FROM tournaments" in sql else {"count": 4},
    )
    monkeypatch.setattr(
        reporting,
        "_schedule_publication_analysis",
        lambda *_: {"conflicts": []},
    )
    monkeypatch.setattr(
        reporting,
        "_bracket_publication_analysis",
        lambda *_: (_ for _ in ()).throw(AssertionError("bracket validation must be skipped")),
    )
    payload = reporting._publication_payload(7)
    assert payload["ready"] is True
    assert payload["blockers"] == []
    assert payload["bracket_validation"]["skipped"] is True


def test_public_view_hides_irrelevant_competition_navigation():
    source = open("frontend-next/src/components/PublicCupView.tsx", encoding="utf-8").read()
    assert 'const showTables=!isMatchcamp' in source
    assert 'const showPlayoffs=!isMatchcamp&&cup.brackets.length>0' in source
    assert 'mobileItems.map' in source
