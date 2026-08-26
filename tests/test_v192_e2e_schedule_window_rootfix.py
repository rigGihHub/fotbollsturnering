from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_safe_demo_capacity_rebuilds_both_window_layers():
    block=APP[APP.index("def _demo_apply_safe_schedule_capacity"):APP.index("def _demo_prepare_schedule")]
    assert 'DELETE FROM pitch_day_windows WHERE tournament_id=?' in block
    assert 'DELETE FROM tournament_day_windows WHERE tournament_id=?' in block
    assert 'ensure_tournament_day_windows(' in block
    assert 'ensure_pitch_day_windows(' in block

def test_e2e_capacity_removes_referee_bottleneck_and_has_large_window():
    block=APP[APP.index("def _demo_apply_safe_schedule_capacity"):APP.index("def _demo_prepare_schedule")]
    assert "pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END" in block
    assert "first_match_time='07:00'" in block
    assert "latest_kickoff_time='23:00'" in block
    assert "referee_mode='Manuell'" in block
