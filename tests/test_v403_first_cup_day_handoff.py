from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_dashboard import build_cup_day_snapshot, cup_day_primary_guidance

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def _match(mid, start, status="not_started"):
    return {
        "id": mid,
        "scheduled_start": start,
        "pitch_number": 1,
        "home_source": "team:1",
        "away_source": "team:2",
        "home_score": None,
        "away_score": None,
        "match_status": status,
    }


def test_version_and_release_note():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert (ROOT / "FIRST_CUP_DAY_HANDOFF_V403.md").exists()


def test_not_started_match_is_start_overdue_before_it_is_result_due():
    now = datetime(2026, 9, 2, 10, 10)
    snap = build_cup_day_snapshot(
        [_match(1, "2026-09-02T10:00:00")],
        now=now,
        match_duration_minutes=30,
        reporting_grace_minutes=10,
    )
    assert [row["id"] for row in snap["start_overdue"]] == [1]
    assert snap["reporting_due"] == []
    guidance = cup_day_primary_guidance(snap, now=now)
    assert guidance["title"] == "Starta matchen"


def test_not_started_match_becomes_result_due_after_duration_and_grace():
    now = datetime(2026, 9, 2, 10, 41)
    snap = build_cup_day_snapshot(
        [_match(1, "2026-09-02T10:00:00")],
        now=now,
        match_duration_minutes=30,
        reporting_grace_minutes=10,
    )
    assert snap["start_overdue"] == []
    assert [row["id"] for row in snap["reporting_due"]] == [1]


def test_published_tournament_day_handoff_targets_cupday_without_extra_query():
    block = APP[APP.index("elif _flow_total and _flow_played < _flow_total:"):APP.index("else:\n    _recommended_page = _recommended_label = None")]
    assert '"Cupdagen", "Öppna cupdagen"' in block
    assert 'tournament["start_date"]' in block
    assert 'tournament["end_date"]' in block
    assert "one_row(" not in block


def test_cupday_ui_offers_start_action_for_late_kickoff():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'Starttid passerad' in section
    assert 'cupday_late_start_' in section
    assert '"▶ Starta match"' in section
    assert "start_overdue_count" in section
