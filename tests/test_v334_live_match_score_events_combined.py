from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v334_release_version():
    assert VERSION == "2026.08.31-348-GUIDED-CUP-SETUP"


def test_score_view_renders_events_for_persisted_result_in_same_workspace():
    assert 'persisted_result = quick_match["home_score"] is not None' in VIEW
    assert 'st.markdown("### ⚽ Livehändelser")' in VIEW
    assert '_render_match_event_entry(\n                    tournament_id, tournament, int(quick_match_id), quick_match, deps' in VIEW


def test_event_entry_is_shared_not_duplicated():
    assert 'def _render_match_event_entry(' in VIEW
    assert VIEW.count('_render_match_event_entry(') == 3
    assert 'deps.save_event_rows([update])' in VIEW
    assert 'deps.save_event_rows([undo_update])' in VIEW


def test_separate_match_events_workspace_remains_available():
    assert 'if reporter_section == reporter_sections[1]:' in VIEW
    assert 'key=f"reporter_event_match_{tournament_id}"' in VIEW
    assert 'Visa tabell för massinmatning' in VIEW
