from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
RESULTS = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v405_version():
    assert VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"


def test_cupday_exact_match_handoff_and_delay_prefill():
    assert 'def _open_cupday_result(match_id):' in APP
    assert 'admin_search_focus_origin_{tid}' in APP
    assert 'def _open_cupday_delay(pitch_number, delay_minutes):' in APP
    assert 'autopilot_delay_pitch_{tid}' in APP
    assert 'autopilot_delay_minutes_{tid}' in APP
    assert 'autopilot_compare_{tid}' in APP
    assert 'Jämför lösningar för förseningen' in APP
    assert 'if _late_mins >= 5:' in APP


def test_pitch_cards_surface_delay_without_new_query():
    block = APP[APP.index('# v404: visible per-pitch focus'):APP.index('# v403: distinguish a late kickoff')]
    assert '_pitch_late_minutes' in block
    assert 'cirka {max(_pitch_late_minutes)} min efter plan' in block
    assert 'all_rows(' not in block
    assert 'one_row(' not in block


def test_results_put_focused_match_first():
    assert 'focus_origin = st.session_state.pop' in RESULTS
    assert 'Öppnad från Cupdagen · matchen ligger först i resultatlistan' in RESULTS
    assert 'if focused_match and focused_match in editor_matches:' in RESULTS
    assert 'editor_matches = [focused_match] +' in RESULTS
