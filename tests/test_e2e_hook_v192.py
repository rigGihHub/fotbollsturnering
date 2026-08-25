from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
E2E = (ROOT / "e2e" / "test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_hook_is_explicitly_environment_gated():
    assert 'os.environ.get("CUPNAVI_E2E") == "1"' in APP
    assert 'E2E: Slutför testcup' in APP

def test_e2e_runner_enables_hook_explicitly():
    assert 'env["CUPNAVI_E2E"]="1"' in E2E

def test_critical_journey_uses_deterministic_hook_not_test_level_combobox():
    journey = E2E.split('def test_full_cup_lifecycle_journey', 1)[1]
    assert 'complete_demo_via_e2e_hook(page,tid' in journey
    assert 'choose_streamlit_option(page,"Testnivå","Hela cupen färdig")' not in journey
