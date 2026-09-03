from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_autopilot import build_referee_no_show_recovery_preview


def _m(mid, start, referee, pitch=1):
    return {
        "id": mid,
        "scheduled_start": start,
        "pitch_number": pitch,
        "home_source": f"team:{mid*2}",
        "away_source": f"team:{mid*2+1}",
        "home_score": None,
        "away_score": None,
        "match_status": "not_started",
        "referee_id": referee,
    }


def test_v411_replaces_absent_referee_without_overlapping_assignments():
    now = datetime.fromisoformat("2026-09-03T09:00")
    matches = [
        _m(1, "2026-09-03T10:00", 10, 1),
        _m(2, "2026-09-03T10:00", 20, 2),
        _m(3, "2026-09-03T11:00", 10, 1),
    ]
    preview = build_referee_no_show_recovery_preview(
        matches,
        referee_id=10,
        candidate_referee_ids=[10, 20, 30],
        now=now,
        match_duration_minutes=45,
    )
    assert preview["affected_match_count"] == 2
    assert preview["replacement_count"] == 2
    assert preview["unresolved_count"] == 0
    first = next(item for item in preview["assignments"] if item["match_id"] == 1)
    assert first["replacement_referee_id"] == 30


def test_v411_reports_unresolved_when_every_candidate_is_busy():
    now = datetime.fromisoformat("2026-09-03T09:00")
    matches = [
        _m(1, "2026-09-03T10:00", 10, 1),
        _m(2, "2026-09-03T10:00", 20, 2),
    ]
    preview = build_referee_no_show_recovery_preview(
        matches,
        referee_id=10,
        candidate_referee_ids=[10, 20],
        now=now,
        match_duration_minutes=45,
    )
    assert preview["replacement_count"] == 0
    assert preview["unresolved_count"] == 1
    assert not preview["recommended"]


def test_v411_ui_is_lazy_and_read_only():
    source = Path("app.py").read_text(encoding="utf-8")
    assert '"Domare uteblir? Hitta ersättare"' in source
    toggle_pos = source.index('"Domare uteblir? Hitta ersättare"')
    query_pos = source.index('"SELECT id,name FROM referees WHERE tournament_id=? ORDER BY name"')
    assert query_pos > toggle_pos
    assert "Analysen ändrar inga domartilldelningar, tider eller planer." in source


def test_v411_version():
    assert Path("VERSION.txt").read_text().strip() == "2026.09.03-414-PITCH-TIMING-MODE"
