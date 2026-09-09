from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_browser_does_not_wait_for_streamlit_autocomplete():
    assert "wait_for_e2e_auto_completion" not in E2E
    assert "seed_completed_cup_fixture(tid)" in E2E

def test_streamlit_product_path_has_no_ci_autocomplete_mutation():
    assert 'os.environ.get("CUPNAVI_E2E") == "1" and testdata_ready' not in APP
    assert "e2e_autocomplete_done_" not in APP
