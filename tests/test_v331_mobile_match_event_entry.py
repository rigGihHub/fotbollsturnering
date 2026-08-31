from pathlib import Path

import pytest

from cupnavi_core.match_event_logic import event_totals_after_update, prepare_quick_event_update

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.08.31-342-POST-SIMPLIFICATION-AUDIT"


def test_match_events_have_touch_first_quick_entry():
    assert 'reporter_event_team_' in VIEW
    assert 'reporter_quick_event_player_' in VIEW
    assert '⚽ + Mål' in VIEW
    assert '🎯 + Assist' in VIEW
    assert '🟨 + Gult' in VIEW
    assert '🟥 + Rött' in VIEW


def test_bulk_table_is_lazy_and_preserved():
    assert 'Visa tabell för massinmatning' in VIEW
    assert 'st.data_editor(' in VIEW
    assert 'if show_table:' in VIEW


def test_quick_entry_uses_existing_concurrency_boundary():
    assert 'outcome = deps.save_event_rows([update])' in VIEW
    assert 'Spelarens händelser ändrades av en annan rapportör' in VIEW


def test_prepare_quick_event_update_keeps_expected_snapshot():
    existing = {7: {"goals": 1, "assists": 0, "yellow_cards": 1, "red_cards": 0}}
    update = prepare_quick_event_update(existing, match_id=12, player_id=7, field="goals", delta=1)
    assert update == {
        "match_id": 12,
        "player_id": 7,
        "goals": 2,
        "assists": 0,
        "yellow_cards": 1,
        "red_cards": 0,
        "expected": {"goals": 1, "assists": 0, "yellow_cards": 1, "red_cards": 0},
    }


def test_quick_event_correction_never_goes_negative():
    existing = {7: {"goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0}}
    assert prepare_quick_event_update(existing, match_id=12, player_id=7, field="goals", delta=-1) is None


def test_quick_event_rejects_unknown_field():
    with pytest.raises(ValueError):
        prepare_quick_event_update({}, match_id=12, player_id=7, field="penalties", delta=1)


def test_event_totals_after_candidate_update_replaces_player_values():
    existing = {
        7: {"goals": 1, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        8: {"goals": 1, "assists": 1, "yellow_cards": 0, "red_cards": 0},
    }
    update = prepare_quick_event_update(existing, match_id=12, player_id=7, field="assists", delta=1)
    assert event_totals_after_update(existing, update) == {"goals": 2, "assists": 2}
