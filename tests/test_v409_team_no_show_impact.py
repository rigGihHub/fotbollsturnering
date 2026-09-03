from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_autopilot import build_team_no_show_impact_preview
from cupnavi_core.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v409_version_and_release_note():
    assert APP_VERSION == "2026.09.03-414-PITCH-TIMING-MODE"
    assert (ROOT / "TEAM_NO_SHOW_IMPACT_V409.md").exists()


def test_no_show_preview_only_counts_future_direct_matches():
    now = datetime.fromisoformat("2026-09-03T10:00:00")
    matches = [
        {"id": 1, "scheduled_start": "2026-09-03T09:00:00", "pitch_number": 1, "home_source": "team:7", "away_source": "team:8", "home_score": 1, "away_score": 0, "match_status": "finished", "stage": "Grupp"},
        {"id": 2, "scheduled_start": "2026-09-03T10:15:00", "pitch_number": 2, "home_source": "team:7", "away_source": "team:9", "home_score": None, "away_score": None, "match_status": "not_started", "stage": "Grupp"},
        {"id": 3, "scheduled_start": "2026-09-03T12:00:00", "pitch_number": 1, "home_source": "team:10", "away_source": "team:7", "home_score": None, "away_score": None, "match_status": "not_started", "stage": "Grupp"},
        {"id": 4, "scheduled_start": "2026-09-03T13:00:00", "pitch_number": 1, "home_source": "winner:1", "away_source": "team:7", "home_score": None, "away_score": None, "match_status": "not_started", "stage": "Slutspel"},
        {"id": 5, "scheduled_start": "2026-09-03T11:00:00", "pitch_number": 3, "home_source": "team:11", "away_source": "team:12", "home_score": None, "away_score": None, "match_status": "not_started", "stage": "Grupp"},
    ]
    preview = build_team_no_show_impact_preview(matches, team_id=7, now=now)
    assert preview["affected_match_count"] == 3
    assert preview["affected_opponent_count"] == 2
    assert [m["match_id"] for m in preview["affected_matches"]] == [2, 3, 4]
    assert preview["recommended_action"] == "confirm_then_review"


def test_v409_ui_is_preview_only_and_reuses_loaded_matches():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Analysera om laget uteblir" in source
    assert "build_team_no_show_impact_preview(\n                                    _day_matches" in source
    assert "CupNavi ändrar inget schema och registrerar ingen walkover automatiskt." in source
