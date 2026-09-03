from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_autopilot import build_autopilot_advice, estimate_pitch_delay_minutes

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def team_id(source):
    return int(source.split(":")[1]) if str(source).startswith("team:") else None


def row(mid, start, pitch, home, away, status="not_started", actual=None):
    return {
        "id": mid,
        "scheduled_start": start,
        "pitch_number": pitch,
        "home_source": f"team:{home}",
        "away_source": f"team:{away}",
        "home_score": None,
        "away_score": None,
        "match_status": status,
        "actual_started_at": actual,
    }


def test_release_version():
    assert VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"


def test_delay_uses_explicit_live_and_actual_start():
    now = datetime(2026, 9, 1, 10, 30)
    rows = [
        row(1, "2026-09-01T10:00:00", 1, 1, 2, "live", "2026-09-01T10:12:00"),
    ]
    delays = estimate_pitch_delay_minutes(rows, now=now, match_duration_minutes=30)
    assert delays[1] == 12


def test_old_not_started_match_does_not_create_fake_delay():
    now = datetime(2026, 9, 1, 11, 0)
    rows = [row(1, "2026-09-01T10:00:00", 1, 1, 2, "not_started")]
    assert estimate_pitch_delay_minutes(rows, now=now, match_duration_minutes=30) == {}


def test_autopilot_warns_about_affected_pitch_matches():
    now = datetime(2026, 9, 1, 10, 30)
    rows = [
        row(1, "2026-09-01T10:00:00", 1, 1, 2, "live", "2026-09-01T10:15:00"),
        row(2, "2026-09-01T10:45:00", 1, 3, 4),
        row(3, "2026-09-01T11:30:00", 1, 5, 6),
    ]
    advice = build_autopilot_advice(
        rows, now=now, match_duration_minutes=30, minimum_rest_minutes=20,
        resolve_team_id=team_id,
    )
    pitch = next(item for item in advice if item["kind"] == "pitch_delay")
    assert pitch["delay_minutes"] == 15
    assert pitch["affected_matches"] == 2
    assert pitch["action"] == "preview_delay"


def test_autopilot_detects_rest_risk_from_real_slippage():
    now = datetime(2026, 9, 1, 10, 30)
    rows = [
        row(1, "2026-09-01T10:00:00", 1, 1, 2, "live", "2026-09-01T10:15:00"),
        row(2, "2026-09-01T10:50:00", 2, 1, 3),
    ]
    advice = build_autopilot_advice(
        rows, now=now, match_duration_minutes=30, minimum_rest_minutes=15,
        resolve_team_id=team_id,
    )
    risk = next(item for item in advice if item["kind"] == "rest_risk")
    assert risk["rest_minutes"] == 5
    assert risk["severity"] == "error"


def test_autopilot_is_preview_first_in_ui():
    assert 'class="cn-autopilot-title">✦ CupNavi Autopilot' in APP
    assert "Ingenting ändras utan att du granskar och godkänner." in APP
    assert '"Jämför lösningar"' in APP
    assert 'st.session_state[f"autopilot_delay_pitch_{tid}"]' in APP
    assert "Förslaget från CupNavi Autopilot är förifyllt." in APP
