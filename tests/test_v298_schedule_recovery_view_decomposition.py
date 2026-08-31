from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "schedule_recovery_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v298_release_and_module_boundary():
    assert VERSION == "2026.08.31-354-ADDRESS-READINESS-FIX"
    assert "class ScheduleRecoveryDependencies" in VIEW
    assert "def render_schedule_recovery_actions" in VIEW
    assert "render_schedule_recovery_actions_module" in APP


def test_sensitive_recovery_writes_remain_in_app_callbacks():
    assert 'UPDATE teams SET late_first_match=0' in APP
    assert 'UPDATE schedule_rules SET consecutive_match_break_minutes=0' in APP
    assert 'UPDATE schedule_rules SET pitch_count=?' in APP
    assert 'UPDATE teams SET late_first_match=0' not in VIEW
    assert 'UPDATE schedule_rules SET consecutive_match_break_minutes=0' not in VIEW
    assert 'UPDATE schedule_rules SET pitch_count=?' not in VIEW


def test_ranked_recovery_ui_owned_by_view():
    assert "CupNavi föreslår en lösning" in VIEW
    assert "Lägg till en extra plan/spelyta" in VIEW
    assert "solutions.sort" in VIEW
