from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_autocomplete_is_environment_gated_and_click_free():
    assert 'os.environ.get("CUPNAVI_E2E") == "1" and testdata_ready' in APP
    assert '_demo_apply_progress_level(tid, "complete")' in APP
    assert 'E2E: Slutför testcup' not in APP
    assert 'env["CUPNAVI_E2E"]="1"' in E2E
    assert 'wait_for_e2e_auto_completion' in E2E
    assert 'get_by_role("button", name="E2E: Slutför testcup"' not in E2E
