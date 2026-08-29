from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "cupnavi_core" / "demo_data_service.py").read_text(encoding="utf-8")


def test_demo_schedule_has_deterministic_capacity_fallback():
    assert "def _demo_apply_safe_schedule_capacity(" in APP
    assert "apply_safe_schedule_capacity(tournament_id, tournament_row)" in APP
    assert "pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END" in SERVICE
    assert "first_match_time='07:00'" in SERVICE
    assert "latest_kickoff_time='23:00'" in SERVICE
    assert 'self.d.run("DELETE FROM pitch_day_windows WHERE tournament_id=?"' in SERVICE


def test_e2e_uses_safe_capacity_before_generation():
    start = SERVICE.index("def prepare_schedule")
    end = SERVICE.index("def apply_progress_level", start)
    prepare = SERVICE[start:end]
    assert 'os.environ.get("CUPNAVI_E2E") == "1"' in prepare
    assert "self.apply_safe_schedule_capacity(tournament_id, tournament_row)" in prepare
    assert "if unresolved and self.d.is_test_environment(tournament_row):" in prepare
