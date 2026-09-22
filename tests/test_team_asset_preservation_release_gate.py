from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADMIN=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
API=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
SEARCH=(ROOT/"frontend-next/src/lib/team-asset-search.ts").read_text(encoding="utf-8")

def bulk_block():
    start=ADMIN.index("async function searchAllTeamAssets")
    end=ADMIN.index("async function saveTeam",start)
    return ADMIN[start:end]

def test_bulk_search_keeps_logo_and_kit_lookup_separate():
    block=bulk_block()
    assert "searchAndSaveTeamAssets" in block
    assert 'if(kitMode!=="none")focuses.push("kit")' in SEARCH
    assert 'if(showLogos&&!existingLogo)focuses.push("logo")' in SEARCH

def test_unverified_search_never_overwrites_existing_kit_fields():
    assert 'if(result.home_verified)Object.assign(patch,{primary_color:' in SEARCH
    assert 'if(result.away_verified)Object.assign(patch,{secondary_color:' in SEARCH
    assert 'if(result.logo_verified&&result.logo_url)Object.assign(patch,{logo_url:' in SEARCH
    assert 'if(result.identity_status!=="exact")' in SEARCH

def test_failed_logo_retry_cannot_discard_verified_kit_data():
    assert "await save(patch);updated=true;" in SEARCH
    assert "setTeams(current=>current.map(item=>item.id===result.id?result:item))" in bulk_block()

def test_rate_limit_stops_bulk_run_instead_of_churning_saved_data():
    block=bulk_block()
    assert "/429|AI_RATE_LIMIT|kapacitetsgräns/" in SEARCH
    assert "if(outcome.stop)" in block
    assert "redan sparade träffar finns kvar" in block
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
