from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTER = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
VERSION = (ROOT / "VERSION.txt").read_text().strip()

def test_v547_version():
    assert VERSION == "2026.09.08-547-BIG-SCOREBOARD-REPORTER-UI"

def test_big_scoreboard_has_large_touch_targets():
    assert "cn-scoreboard-team" in REPORTER
    assert "min-height:76px" in REPORTER
    assert "font-size:3.7rem" in REPORTER
    assert "Tryck stort +/−" in REPORTER

def test_setup_driven_event_gates_survive_scoreboard_redesign():
    assert "_player_event_tracking = _scorer_tracking or _assist_tracking or _card_tracking" in REPORTER
    assert "if _scorer_tracking:" in REPORTER
    assert "if _assist_tracking:" in REPORTER
    assert "if _card_tracking:" in REPORTER

def test_correction_window_survives_scoreboard_redesign():
    assert "REPORTER_CORRECTION_WINDOW_SECONDS = 15" in REPORTER
    assert "_render_reporter_correction_window(int(quick_match_id))" in REPORTER
