from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
LOGIC=(ROOT/"cupnavi_core/match_reporter_logic.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_canonical_snapshot_is_used_by_reporter_quick_save():
    assert "def result_snapshot(" in LOGIC
    assert "before = result_snapshot(quick_match)" in APP

def test_bulk_preparation_uses_same_snapshot_contract():
    assert '"expected": result_snapshot(original)' in LOGIC

def test_conditional_update_remains_in_app_persistence_boundary():
    assert "def update_match_result_if_unchanged(" in APP
    assert "def update_match_result_if_unchanged(" not in LOGIC

def test_release_is_v211():
    assert VERSION=="2026.08.28-247-PUBLIC-TEAM-MOBILE-QA"
    assert "Version v.1.247" in APP
