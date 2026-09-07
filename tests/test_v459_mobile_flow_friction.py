from datetime import datetime
from pathlib import Path

from cupnavi_core.mobile_flow import mobile_match_preview

VERSION = "2026.09.07-497-MY-TEAMS-NOTICES-POLISH"
APP = Path("app.py").read_text(encoding="utf-8")
PORTAL = Path("cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")


def _row(match_id, start, pitch=1):
    return {
        "id": match_id,
        "scheduled_start": start,
        "pitch_number": pitch,
        "home_score": None,
        "away_score": None,
    }


def test_version_is_v459():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_mobile_match_preview_prefers_next_matches():
    rows = [
        _row(1, "2026-09-05T09:00"),
        _row(2, "2026-09-05T11:00"),
        _row(3, "2026-09-05T13:00"),
        _row(4, "2026-09-05T15:00"),
    ]
    preview = mobile_match_preview(
        rows, now=datetime(2026, 9, 5, 10, 0), limit=3
    )
    assert [row["id"] for row in preview] == [2, 3, 4]


def test_mobile_match_preview_uses_latest_when_day_is_finished():
    rows = [
        _row(1, "2026-09-05T09:00"),
        _row(2, "2026-09-05T11:00"),
        _row(3, "2026-09-05T13:00"),
        _row(4, "2026-09-05T15:00"),
    ]
    preview = mobile_match_preview(
        rows, now=datetime(2026, 9, 5, 18, 0), limit=3
    )
    assert [row["id"] for row in preview] == [2, 3, 4]


def test_team_readiness_details_are_collapsed_by_default():
    assert 'with st.expander("Visa hela checklistan", expanded=False):' in PORTAL


def test_long_team_schedule_is_progressively_disclosed():
    assert 'mobile_match_preview(matches, now=datetime.now(), limit=3)' in PORTAL
    assert 'with st.expander(f"Visa alla {len(matches)} matcher", expanded=False):' in PORTAL


def test_full_schedule_remains_available():
    assert 'for match_row in matches:' in PORTAL
    assert 'if int(match_row["id"]) in _preview_ids:' in PORTAL
