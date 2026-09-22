import pytest
from fastapi import HTTPException
from cupnavi_api import main as api
from cupnavi_core import ai_kit_suggestion as core


@pytest.fixture
def endpoint(monkeypatch):
    monkeypatch.setattr(api, "_admin_identity", lambda _: {"id": 1})
    monkeypatch.setattr(api, "admin_cupinfo", lambda *_: {"arena_address": "Örebro"})
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    calls = []
    def lookup(*args, **kwargs):
        calls.append((args, kwargs))
        return {"identity_status": "exact", "home_verified": True, "home_pattern": "Vertikala ränder", "logo_verified": False}
    monkeypatch.setattr(api, "suggest_team_kit", lookup)
    return calls


@pytest.mark.parametrize("club", ["AIK", "Hammarby", "Örebro SK", "BK Häcken"])
def test_builtin_register_never_prevents_web_lookup(endpoint, club):
    result = api.search_admin_team_kit(1, api.KitSearchRequest(team_name=club, kit_mode="home"), "Bearer test")
    assert len(endpoint) == 1
    assert endpoint[0][1]["kit_mode"] == "home"
    assert result["home_verified"] and result["home_pattern"] == "Vertikala ränder"
    assert result["away_verified"] is False


def test_missing_provider_is_explicit_not_fake_success(endpoint, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(HTTPException) as caught:
        api.search_admin_team_kit(1, api.KitSearchRequest(team_name="AIK"), "Bearer test")
    assert caught.value.status_code == 503
    assert "Ingen webbsökning" in caught.value.detail
    assert not endpoint


def test_home_mode_all_passes_exclude_away_and_logo_queries():
    for _, instruction in core._search_strategies("AIK", search_focus="kit", kit_mode="home"):
        assert "Sök endast hemmatröjans färger och mönster" in instruction
        assert "Sök hemma och borta" not in instruction
        assert "away kit" not in instruction


def test_logo_mode_does_not_request_kit_search():
    for _, instruction in core._search_strategies("AIK", search_focus="logo"):
        assert "Sök inga matchställ" in instruction
        assert "Sök hemma och borta" not in instruction


def test_home_ready_stops_after_one_pass_and_strips_unsolicited_away(monkeypatch):
    calls = []
    def lookup(*args, **kwargs):
        calls.append(kwargs)
        return {"identity_status": "exact", "club_match": "AIK Solna", "home_verified": True,
                "away_verified": True, "away_sources": ["https://example.org/away"],
                "home_pattern": "Helfärgad", "found": True}
    monkeypatch.setattr(core, "_request_suggestion", lookup)
    result = core.suggest_team_kit("AIK", "test", kit_mode="home", use_cache=False)
    assert len(calls) == 1 and calls[0]["kit_mode"] == "home"
    assert result["home_verified"]
    assert not result["away_verified"] and result["away_sources"] == []


def test_cache_separates_modes():
    args = ("AIK", "", "", "", "", "model")
    assert core._cache_key(*args, kit_mode="home") != core._cache_key(*args, kit_mode="both")
