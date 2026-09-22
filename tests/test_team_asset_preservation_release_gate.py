from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADMIN=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
API=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")

def bulk_block():
    start=ADMIN.index("async function searchAllTeamAssets")
    end=ADMIN.index("async function saveTeam",start)
    return ADMIN[start:end]

def test_bulk_search_keeps_logo_and_kit_lookup_separate():
    block=bulk_block()
    assert "const missingLogo=!team.logo_url" in block
    assert 'const searchFocus=missingLogo?"logo":"kit"' in block
    assert '?"logo":"all"' not in block

def test_unverified_search_never_overwrites_existing_kit_fields():
    block=bulk_block()
    assert '...(suggestion.home_verified?{primary_color:' in block
    assert '...(suggestion.away_verified?{secondary_color:' in block
    assert '...(suggestion.logo_verified?{logo_url:' in block

def test_failed_logo_retry_cannot_discard_verified_kit_data():
    block=bulk_block()
    assert "A logo retry must never discard already verified kit data." in block
    assert "catch{/* A logo retry" in block

def test_rate_limit_stops_bulk_run_instead_of_churning_saved_data():
    block=bulk_block()
    assert "/429|AI_RATE_LIMIT|kapacitetsgräns/" in block
    assert "stoppade resten för att skydda redan sparad data" in block
    assert "break;" in block
    assert 'response.status === 429 ? serverDetail || "För många försök' in ADMIN

def test_kit_search_rate_limit_is_not_logged_as_bad_gateway():
    endpoint=API.index("def search_admin_team_kit")
    block=API[API.index("except RuntimeError as exc:", endpoint):API.index("@app.delete", endpoint)]
    assert '"AI_RATE_LIMIT" in raw_detail' in block
    assert "status_code=429" in block
    assert '"Retry-After"' in block
    assert "status_code=502" in block

def test_manual_suggestion_only_applies_verified_parts():
    start=ADMIN.index("function applyKitSuggestion")
    end=ADMIN.index("async function searchAllTeamAssets",start)
    block=ADMIN[start:end]
    assert "kitSuggestion.home_verified" in block
    assert "kitSuggestion.away_verified" in block
    assert "kitSuggestion.logo_verified" in block
