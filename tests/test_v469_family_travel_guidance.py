from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import build_family_travel_guidance

VERSION = "2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"
APP = Path("app.py").read_text(encoding="utf-8")
VIEW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def _item(start, pitch):
    return {"start": start, "match": {"pitch_number": pitch}, "favorite_team_ids": (1,)}


def test_version_is_v469():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_travel_margin_is_after_estimated_match_end():
    step = {
        "next_item": _item(datetime(2026, 9, 5, 10, 0), 1),
        "following_item": _item(datetime(2026, 9, 5, 11, 0), 2),
        "from_pitch": 1,
        "to_pitch": 2,
    }
    result = build_family_travel_guidance(
        step, {(1, 2): 12}, match_duration_minutes=40
    )
    assert result["planned_transfer_minutes"] == 12
    assert result["post_match_window_minutes"] == 20
    assert result["margin_minutes"] == 8
    assert result["status"] == "tight"


def test_missing_travel_time_is_explicit():
    step = {
        "next_item": _item(datetime(2026, 9, 5, 10, 0), 1),
        "following_item": _item(datetime(2026, 9, 5, 11, 10), 3),
        "from_pitch": 1,
        "to_pitch": 3,
    }
    result = build_family_travel_guidance(
        step, {}, match_duration_minutes=40
    )
    assert result["available"] is False
    assert result["status"] == "missing_travel_time"
    assert result["margin_minutes"] is None


def test_insufficient_margin_is_detected():
    step = {
        "next_item": _item(datetime(2026, 9, 5, 10, 0), 1),
        "following_item": _item(datetime(2026, 9, 5, 10, 50), 2),
        "from_pitch": 1,
        "to_pitch": 2,
    }
    result = build_family_travel_guidance(
        step, {(1, 2): 15}, match_duration_minutes=40
    )
    assert result["margin_minutes"] == -5
    assert result["status"] == "insufficient"


def test_same_pitch_needs_no_travel_lookup():
    step = {
        "next_item": _item(datetime(2026, 9, 5, 10, 0), 2),
        "following_item": _item(datetime(2026, 9, 5, 11, 5), 2),
        "from_pitch": 2,
        "to_pitch": 2,
    }
    result = build_family_travel_guidance(
        step, {}, match_duration_minutes=40
    )
    assert result["available"] is True
    assert result["planned_transfer_minutes"] == 0
    assert result["margin_minutes"] == 25
    assert result["status"] == "same_pitch"


def test_view_uses_existing_travel_table_only_for_multi_favorite_followup():
    assert "build_family_travel_guidance(" in VIEW
    assert "FROM pitch_travel_times WHERE tournament_id=?" in VIEW
    assert "SELECT * FROM schedule_rules WHERE tournament_id=?" in VIEW
    assert "Planerad förflyttning:" in VIEW
    assert "Förflyttningstid mellan planerna saknas." in VIEW
    assert "marginal efter beräknad matchslut:" in VIEW
    assert ".cn-family-next-card .travel{" in STYLE
