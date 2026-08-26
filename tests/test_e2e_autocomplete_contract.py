from pathlib import Path

E2E = Path(__file__).resolve().parents[1] / "e2e" / "test_streamlit_critical_journey.py"
APP = Path(__file__).resolve().parents[1] / "app.py"


def test_e2e_autocomplete_does_not_wait_for_test_level_widget():
    text = E2E.read_text(encoding="utf-8")
    assert 'wait_for_e2e_auto_completion' in text
    assert 'Timed out waiting for persisted demo data' in text
    assert 'wait_until_enabled(page.get_by_label("Testnivå"' not in text


def test_server_side_autocomplete_is_e2e_gated():
    text = APP.read_text(encoding="utf-8")
    assert 'os.environ.get("CUPNAVI_E2E") == "1" and testdata_ready' in text
    assert '_demo_apply_progress_level(tid, "complete")' in text
