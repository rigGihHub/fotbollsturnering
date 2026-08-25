from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")
WF=(ROOT/".github/workflows/cross-browser.yml").read_text(encoding="utf-8")

def test_e2e_covers_full_core_lifecycle():
    for phrase in (
        "Skapa testdata:",
        "E2E: Slutför testcup",
        "assert_complete_database",
        "competition_classes",
        "stage<>'Gruppspel'",
        "Schema & resultat",
        "Tabeller",
        "Slutspel",
        "Statistik",
        "Cupinfo",
        'viewport={"width":390,"height":844}',
        "public_only=1",
        "cn-mobile-bottom-nav",
    ):
        assert phrase in E2E

def test_e2e_runs_all_browser_engines():
    assert '["chromium","firefox","webkit"]' in E2E
    assert "test_streamlit_critical_journey.py" in WF
