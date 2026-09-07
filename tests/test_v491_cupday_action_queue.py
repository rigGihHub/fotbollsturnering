from datetime import datetime, timedelta
from pathlib import Path

from cupnavi_core.cup_day_dashboard import build_cup_day_action_queue

VERSION = "2026.09.07-507-REVIEWED-DOCUMENT-SCHEDULE-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")


def _match(mid, pitch=1):
    return {"id": mid, "pitch_number": pitch, "scheduled_start": "2026-09-06T12:00:00"}


def test_version_is_v491():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_missing_result_beats_overdue_start_and_readiness():
    queue = build_cup_day_action_queue(
        {"reporting_due": [_match(9, 2)], "start_overdue": [_match(7, 1)]},
        readiness=[{"kind":"missing_referee","severity":"error","title":"Domare saknas","detail":"x","match_id":3,"pitch_number":1,"action":"open_referees"}],
        max_items=5,
    )
    assert [item["action"] for item in queue[:3]] == ["open_result", "start_match", "open_referees"]


def test_queue_preserves_safe_start_row_for_callback():
    row = _match(7, 1)
    queue = build_cup_day_action_queue({"start_overdue": [row]})
    assert queue[0]["match_row"] is row
    assert queue[0]["action"] == "start_match"


def test_queue_is_limited_and_deterministic():
    queue = build_cup_day_action_queue({"reporting_due": [_match(3,3), _match(1,1), _match(2,2)]}, max_items=2)
    assert [item["match_id"] for item in queue] == [1,2]


def test_ui_uses_existing_callbacks_without_explicit_queue_rerun():
    assert '<div class="cn-section-head">Åtgärda nu</div>' in APP
    assert "on_click=_open_cupday_result" in APP
    assert "on_click=_cupday_set_match_status_callback" in APP
    assert "on_click=_open_cupday_delay" in APP
    start = APP.index('# v491: one ranked operational queue')
    end = APP.index('if _day_readiness:', start)
    assert 'st.rerun()' not in APP[start:end]


def test_schema_remains_v32():
    assert "LATEST_SCHEMA_VERSION = 32" in Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
