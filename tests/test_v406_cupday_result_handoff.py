from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text().strip()
RESULTS = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text()
APP = (ROOT / "app.py").read_text()


def test_v406_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"


def test_next_same_pitch_is_in_memory_and_pending_only():
    assert "def next_same_pitch_match(matches, completed_match):" in RESULTS
    block = RESULTS[RESULTS.index("def next_same_pitch_match"):RESULTS.index("def prepare_admin_result_updates")]
    assert 'row["pitch_number"] != completed_match["pitch_number"]' in block
    assert 'row["home_score"] is not None and row["away_score"] is not None' in block
    assert "deps.all_rows" not in block


def test_result_workspace_shows_same_pitch_handoff():
    assert 'cupday_result_completed_match_{tid}' in RESULTS
    assert "Resultatet är klart" in RESULTS
    assert "Nästa på Plan" in RESULTS
    assert "Öppna nästa match i Cupdagen" in RESULTS


def test_save_marks_only_completed_cupday_focus():
    assert 'st.session_state.get(_focus_origin_key) == "Cupdagen"' in APP
    assert '_saved["home_score"] is not None' in APP
    assert '_saved["away_score"] is not None' in APP
    assert 'st.session_state[f"cupday_result_completed_match_{tid}"]' in APP
