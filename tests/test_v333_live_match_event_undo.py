from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()

def test_v333_release_and_one_tap_undo_contract():
    assert (ROOT / "VERSION.txt").read_text().strip() == "2026.08.31-351-SETUP-COMPLETION-HANDOFF"
    assert "↩️ Ångra senaste" in WORKSPACE
    assert "quick_last_event_detail_key" in WORKSPACE
    assert "target_player_id = int(last_detail.get(\"player_id\"" in WORKSPACE
    assert "field=target_field, delta=-1" in WORKSPACE
    assert "undo_outcome = deps.save_event_rows([undo_update])" in WORKSPACE
    assert "Händelsen ändrades av en annan rapportör" in WORKSPACE
