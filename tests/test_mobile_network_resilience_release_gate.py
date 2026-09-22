from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=(ROOT/"frontend-next/src/components/PublicCupView.tsx").read_text(encoding="utf-8")
ADMIN=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
REPORTER=(ROOT/"frontend-next/src/components/reporter-client.tsx").read_text(encoding="utf-8")
QUEUE=(ROOT/"frontend-next/src/lib/reporter-offline.ts").read_text(encoding="utf-8")
SW=(ROOT/"frontend-next/public/sw.js").read_text(encoding="utf-8")
CSS=(ROOT/"frontend-next/src/app/public-atmosphere-v2671.css").read_text(encoding="utf-8")

def test_public_mobile_defers_heavy_secondary_data():
    assert 'tab!=="table"' in PUBLIC
    assert "IntersectionObserver" in PUBLIC
    assert "filteredMatches.slice(0,visibleCount)" in PUBLIC

def test_public_mobile_layout_protects_long_names_and_touch_filters():
    assert "white-space:normal!important" in CSS
    assert "grid-template-columns:repeat(3,1fr)!important" in CSS
    assert "Public v3.3 mobile cupday table/nav fix" in CSS
    assert ".page-shell--public-v3 .texttv--standings .texttv__scroll{max-width:100%!important;overflow:hidden!important}" in CSS
    assert "section:has(.table-stack){padding-bottom:118px!important}" in CSS

def test_public_mobile_tables_and_footer_do_not_hide_content():
    assert "Public v3.2 mobile QA" in CSS
    assert "Public v3.3 mobile cupday table/nav fix" in CSS
    assert ".page-shell--public-v3 .texttv--standings table" in CSS
    assert "min-width:0!important" in CSS
    assert "table-layout:fixed!important" in CSS
    assert "grid-template-columns:repeat(3,1fr)!important" in CSS
    assert "padding-bottom:calc(122px + env(safe-area-inset-bottom))!important" in CSS

def test_public_cupinfo_hides_missing_match_duration():
    assert "const hasMatchDuration=(cup.tournament.minutes_per_half??0)>0" in PUBLIC
    assert "{hasMatchDuration&&<div><span>Matchtid</span>" in PUBLIC
    assert '<div><span>Matchtid</span><b>{(cup.tournament.minutes_per_half??0)>0' not in PUBLIC

def test_public_cupinfo_is_visitor_oriented():
    assert "public-info-hero--visitor" in PUBLIC
    assert "Hitta rätt från start" in PUBLIC
    assert "Behöver du fråga något?" in PUBLIC
    assert "Vägen vidare" in PUBLIC
    assert "visitorInfoText" in PUBLIC

def test_admin_session_survives_transient_api_failure():
    assert "Tillfälligt anslutningsproblem. Din inloggning ligger kvar" in ADMIN
    assert "retryTimer=window.setTimeout(restoreSession,2200)" in ADMIN
    assert "localStorage.removeItem(TOKEN_KEY)" in ADMIN

def test_reporter_has_persistent_offline_queue_and_conflict_states():
    assert "cupnavi_reporter_queue_v1" in QUEUE
    assert "localStorage.setItem(QUEUE_KEY" in QUEUE
    assert '"queued"|"uncertain"|"conflict"' in QUEUE
    assert "reporter-network" in REPORTER

def test_service_worker_keeps_reporter_shell_available():
    assert '"/reporter"' in SW
    assert "fetch" in SW
