from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_reporter_has_mobile_touch_targets():
    assert 'min-height: 52px' in VIEW


def test_saved_quick_result_exposes_events_in_same_match_flow():
    assert 'persisted_result = quick_match["home_score"] is not None' in VIEW
    assert '### ⚽ Livehändelser' in VIEW
    assert '_render_match_event_entry(' in VIEW
    assert 'senast sparade resultatet' in VIEW


def test_existing_concurrency_save_callback_remains_in_use():
    assert 'deps.save_quick_result(tournament_id, quick_match, quick_home_score, quick_away_score)' in VIEW
