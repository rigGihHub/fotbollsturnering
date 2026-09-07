from pathlib import Path
from cupnavi_core.playoff_dependency_safety import recovery_eligibility

VERSION = "2026.09.07-497-MY-TEAMS-NOTICES-POLISH"
APP = Path("app.py").read_text(encoding="utf-8")
SCHEDULE = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")


def _value(row, key, default=None):
    return row.get(key, default)


def test_version_is_v477():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_unused_downstream_with_result_can_be_reset():
    allowed, reason = recovery_eligibility(
        {
            "match_status": "not_started",
            "actual_started_at": None,
            "home_score": 1,
            "away_score": 0,
            "event_count": 0,
        },
        row_value=_value,
    )
    assert allowed is True
    assert "inte startat" in reason


def test_live_downstream_cannot_be_reset():
    allowed, _ = recovery_eligibility(
        {"match_status": "live", "actual_started_at": None, "event_count": 0},
        row_value=_value,
    )
    assert allowed is False


def test_actual_start_time_blocks_reset_even_if_status_is_wrong():
    allowed, reason = recovery_eligibility(
        {"match_status": "not_started", "actual_started_at": "2026-09-05T14:00:00", "event_count": 0},
        row_value=_value,
    )
    assert allowed is False
    assert "starttid" in reason


def test_match_events_block_reset():
    allowed, reason = recovery_eligibility(
        {"match_status": "not_started", "actual_started_at": None, "event_count": 2},
        row_value=_value,
    )
    assert allowed is False
    assert "matchhändelser" in reason


def test_recovery_write_is_guarded_and_audited():
    start = APP.index("def _reset_unused_playoff_downstream_match(")
    end = APP.index("def update_match_result_if_unchanged(", start)
    block = APP[start:end]
    assert "recovery_eligibility(" in block
    assert "actual_started_at IS NULL" in block
    assert "NOT EXISTS (SELECT 1 FROM player_match_stats" in block
    assert "playoff_downstream_reset" in block
    assert "record_audit(" in block


def test_recovery_clears_only_result_state_not_sources_or_schedule():
    start = APP.index("def _reset_unused_playoff_downstream_match(")
    end = APP.index("def update_match_result_if_unchanged(", start)
    block = APP[start:end]
    assert "home_score=NULL" in block
    assert "away_score=NULL" in block
    assert "home_penalties=NULL" in block
    assert "away_penalties=NULL" in block
    assert "decided_winner_id=NULL" in block
    assert "home_source=" not in block
    assert "away_source=" not in block
    assert "scheduled_start=" not in block
    assert "pitch_number=" not in block


def test_schedule_ui_offers_recovery_for_blocked_dependency():
    assert "reset_unused_playoff_downstream_match" in SCHEDULE
    assert "↩ Återställ oanvänd match" in SCHEDULE
    assert "_downstream_ids" in SCHEDULE


def test_dependency_payload_keeps_downstream_ids():
    assert 'tuple(dependency.get("downstream_match_ids", ()))' in APP
