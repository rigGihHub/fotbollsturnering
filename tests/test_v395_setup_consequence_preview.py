from pathlib import Path
from cupnavi_core.initial_setup_logic import setup_consequence_preview

VERSION = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_release_version():
    root=Path(__file__).resolve().parents[1]
    assert (root / "VERSION.txt").read_text().strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in (root / "app.py").read_text()


def test_preview_reports_good_margin_without_claiming_schedule_duration():
    preview=setup_consequence_preview(team_count=8,total_matches=16,match_minutes=30,available_minutes=720)
    assert preview["team_count"] == 8
    assert preview["total_matches"] == 16
    assert preview["pitch_time_minutes"] == 480
    assert preview["utilization_percent"] == 67
    assert preview["margin_label"] == "God marginal"


def test_preview_warns_when_match_demand_exceeds_pitch_time():
    preview=setup_consequence_preview(team_count=12,total_matches=30,match_minutes=30,available_minutes=720)
    assert preview["utilization_percent"] == 125
    assert preview["margin_tone"] == "over"
