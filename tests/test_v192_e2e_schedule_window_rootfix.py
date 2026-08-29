from pathlib import Path

SERVICE = (Path(__file__).resolve().parents[1] / "cupnavi_core" / "demo_data_service.py").read_text(encoding="utf-8")


def _safe_capacity_block():
    start = SERVICE.index("def apply_safe_schedule_capacity")
    end = SERVICE.index("def prepare_schedule", start)
    return SERVICE[start:end]


def test_safe_demo_capacity_rebuilds_both_window_layers():
    block = _safe_capacity_block()
    assert 'DELETE FROM pitch_day_windows WHERE tournament_id=?' in block
    assert 'DELETE FROM tournament_day_windows WHERE tournament_id=?' in block
    assert 'self.d.ensure_tournament_day_windows(' in block
    assert 'self.d.ensure_pitch_day_windows(' in block


def test_e2e_capacity_removes_referee_bottleneck_and_has_large_window():
    block = _safe_capacity_block()
    assert "pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END" in block
    assert "first_match_time='07:00'" in block
    assert "latest_kickoff_time='23:00'" in block
    assert "referee_mode='Manuell'" in block
