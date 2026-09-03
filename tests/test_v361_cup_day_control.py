from pathlib import Path
from datetime import datetime
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load():
    spec = importlib.util.spec_from_file_location("cup_day_dashboard_v361", ROOT / "cupnavi_core" / "cup_day_dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_live_day_snapshot_separates_now_next_and_reporting_due():
    mod = _load()
    now = datetime(2026, 9, 1, 10, 0)
    matches = [
        {"id":1,"scheduled_start":"2026-09-01T09:00:00","home_score":2,"away_score":1,"pitch_number":1},
        {"id":2,"scheduled_start":"2026-09-01T09:10:00","home_score":None,"away_score":None,"pitch_number":2},
        {"id":3,"scheduled_start":"2026-09-01T09:40:00","home_score":None,"away_score":None,"pitch_number":1},
        {"id":4,"scheduled_start":"2026-09-01T10:30:00","home_score":None,"away_score":None,"pitch_number":2},
        {"id":5,"scheduled_start":"2026-09-01T12:00:00","home_score":None,"away_score":None,"pitch_number":1},
    ]
    snap = mod.build_cup_day_snapshot(
        matches,
        now=now,
        match_duration_minutes=30,
        reporting_grace_minutes=10,
        upcoming_window_minutes=45,
    )
    assert len(snap["completed"]) == 1
    assert len(snap["reporting_due"]) == 1
    assert len(snap["live"]) == 1
    assert len(snap["next_window"]) == 1
    assert len(snap["upcoming"]) == 2


def test_cup_day_is_mobile_operational_page_in_match_navigation():
    assert '"Cupdagen"' in APP
    assert '("Cupdagen", "Cupdagen")' in APP
    assert 'if admin_page == "Cupdagen":' in APP
    assert "Mobil kontrollcentral" in APP
    assert "Kräver uppmärksamhet" in APP
    assert "Nästa matcher" in APP
    assert "Planstatus" in APP


def test_cup_day_has_direct_operational_actions():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert "Registrera resultat" in section
    assert "Hantera försening" in section
    assert "Öppna schema" in section
    assert 'args=("Cupverktyg",)' in section


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.03-427-TRAVEL-RULES-FLOW"' in APP
