
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
LOGIC=(ROOT/"cupnavi_core/match_reporter_logic.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_reporter_uses_shared_playable_match_logic_in_result_and_event_flows():
    assert APP.count("select_playable_matches(") >= 2

def test_bulk_projection_is_extracted():
    assert "def build_bulk_result_rows(" in LOGIC
    assert "build_bulk_result_rows(" in APP

def test_persistence_and_locking_remain_in_app_boundary():
    assert "update_match_result_if_unchanged(" in APP
    assert "with db() as con:" in APP
    assert "update_match_result_if_unchanged(" not in LOGIC

def test_release_is_v209():
    assert VERSION=="2026.08.28-261-HEAVY-ADMIN-PERFORMANCE"
    assert "Version v.1.261" in APP
