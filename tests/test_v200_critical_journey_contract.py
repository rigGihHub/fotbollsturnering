
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_public_sections_require_domain_content_not_only_no_traceback():
    for token in [
        '("Schema & resultat", "matches", team_token)',
        '("Tabeller", "tables", group_token)',
        '("Slutspel", "playoffs", "FINAL")',
        '("Statistik", "stats", "Skytteliga")',
        '("Cupinfo", "info", "Cupens regler")',
    ]:
        assert token in E2E

def test_active_tournament_has_real_browser_regression_guard():
    assert "def test_active_tournament_switch_survives_browser_rerun" in E2E
    assert 'choose_streamlit_option(page,"Aktiv turnering",first)' in E2E
    assert "page.reload(wait_until=" in E2E
    assert 'selector.input_value() == first' in E2E

def test_release_is_v200():
    assert VERSION == "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"
