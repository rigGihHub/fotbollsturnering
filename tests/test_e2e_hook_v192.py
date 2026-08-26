from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_is_click_free_after_demo_creation():
    assert "def seed_completed_cup_fixture(" in E2E
    assert "E2E: Slutför testcup" not in E2E
    assert "wait_for_e2e_auto_completion" not in E2E

def test_no_e2e_specific_lifecycle_mutation_in_app_render():
    assert "e2e_autocomplete_done_" not in APP
    assert "E2E auto-completion failed:" not in APP
