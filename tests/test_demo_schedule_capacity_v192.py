from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_demo_schedule_has_deterministic_capacity_fallback():
    assert "def _demo_apply_safe_schedule_capacity(" in APP
    assert "pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END" in APP
    assert "first_match_time='07:00'" in APP
    assert "latest_kickoff_time='23:00'" in APP
    assert 'run("DELETE FROM pitch_day_windows WHERE tournament_id=?"' in APP

def test_e2e_uses_safe_capacity_before_generation():
    prepare = APP[APP.index("def _demo_prepare_schedule"):APP.index("def _demo_apply_progress_level")]
    assert 'os.environ.get("CUPNAVI_E2E") == "1"' in prepare
    assert "_demo_apply_safe_schedule_capacity(tournament_id, tournament_row)" in prepare
    assert "if unresolved and is_test_environment(tournament_row):" in prepare
