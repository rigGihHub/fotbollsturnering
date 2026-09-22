from pathlib import Path

from cupnavi_core.ai_kit_suggestion import _merge_compatible_results, _search_strategies


ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
API = (ROOT / "cupnavi_api/main.py").read_text(encoding="utf-8")
CORE = (ROOT / "cupnavi_core/ai_kit_suggestion.py").read_text(encoding="utf-8")


def _result(club, *, home=False, away=False, logo=False):
    return {
        "club_match": club,
        "identity_status": "exact",
        "confidence": "high",
        "found": home or away,
        "home_verified": home,
        "home_pattern": "Helfärgad",
        "home_color_1": "#111111",
        "home_color_2": "#FFFFFF",
        "home_sources": ["https://club.example/home"] if home else [],
        "home_evidence": "hemma" if home else "",
        "away_verified": away,
        "away_pattern": "Helfärgad",
        "away_color_1": "#FFFFFF",
        "away_color_2": "#111111",
        "away_sources": ["https://club.example/away"] if away else [],
        "away_evidence": "borta" if away else "",
        "logo_verified": logo,
        "logo_url": "https://club.example/logo.svg" if logo else "",
        "logo_source_url": "https://club.example" if logo else "",
        "sources": [],
    }


def test_search_has_separate_kit_and_logo_modes_and_bypasses_stale_cache():
    assert 'search_focus: str = "kit"' in API
    assert "force_refresh: bool = False" in API
    assert 'searchAssets("kit")' in UI
    assert 'searchAssets("logo")' in UI
    assert "force_refresh:true" in UI
    assert "SEARCH_VERSION" in CORE


def test_cup_venue_is_explicitly_rejected_as_club_identity_evidence():
    _, instruction = _search_strategies("AIK P2014", location="Örebro", search_focus="kit")[0]
    assert "ALDRIG användas som belägg för klubbens hemort" in instruction


def test_complementary_assets_merge_only_for_the_same_club():
    merged = _merge_compatible_results(_result("AIK Solna", home=True), _result("AIK Solna", logo=True))
    assert merged["home_verified"] is True
    assert merged["logo_verified"] is True

    separate = _merge_compatible_results(_result("AIK Solna", home=True), _result("AIK Härnösand", logo=True))
    assert not (separate["home_verified"] and separate["logo_verified"])


def test_search_result_requires_explicit_user_application():
    search_block = UI[UI.index("async function searchAssets"):UI.index("function applyKitSuggestion")]
    assert "setTeamDraft" not in search_block
    assert "Använd verifierade uppgifter" in UI
    bulk_search = (ROOT / "frontend-next/src/lib/team-asset-search.ts").read_text(encoding="utf-8")
    assert 'result.identity_status!=="exact"' in bulk_search
