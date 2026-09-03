from datetime import datetime
from pathlib import Path

from cupnavi_core.autopilot_recovery import compare_pitch_delay_recovery_options

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def tid(source):
    return int(source.split(":")[1]) if str(source).startswith("team:") else None


def m(mid, start, pitch, home, away, referee=None):
    return {
        "id": mid,
        "scheduled_start": start,
        "pitch_number": pitch,
        "home_source": f"team:{home}",
        "away_source": f"team:{away}",
        "home_score": None,
        "away_score": None,
        "referee_id": referee,
        "match_no": mid,
    }


RULES = {
    "halves": 1,
    "minutes_per_half": 20,
    "halftime_minutes": 0,
    "minimum_team_rest_minutes": 10,
    "pitch_break_minutes": 0,
}


def test_release_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"


def test_gap_absorption_moves_fewer_matches_than_full_cascade():
    rows = [
        m(1, "2026-09-01T10:30:00", 1, 1, 2),
        m(2, "2026-09-01T11:10:00", 1, 3, 4),  # 20 minute gap after match 1
        m(3, "2026-09-01T11:30:00", 1, 5, 6),
    ]
    options = compare_pitch_delay_recovery_options(
        rows,
        pitch_number=1,
        delay_minutes=10,
        now=datetime(2026, 9, 1, 10, 0),
        match_duration_minutes=20,
        pitch_break_minutes=0,
        rules=RULES,
        resolve_team_id=tid,
    )
    absorb = next(o for o in options if o["kind"] == "absorb_gaps")
    full = next(o for o in options if o["kind"] == "shift_all")
    assert absorb["changed_matches"] < full["changed_matches"]
    assert absorb["shifted_minutes"] < full["shifted_minutes"]


def test_move_next_is_offered_when_other_pitch_is_free_and_gap_recovers_delay():
    rows = [
        m(1, "2026-09-01T10:30:00", 1, 1, 2),
        m(2, "2026-09-01T11:00:00", 1, 3, 4),
        m(3, "2026-09-01T10:00:00", 2, 7, 8),
        m(4, "2026-09-01T11:30:00", 2, 9, 10),
    ]
    options = compare_pitch_delay_recovery_options(
        rows,
        pitch_number=1,
        delay_minutes=10,
        now=datetime(2026, 9, 1, 10, 0),
        match_duration_minutes=20,
        pitch_break_minutes=0,
        rules=RULES,
        resolve_team_id=tid,
    )
    move = next(o for o in options if o["kind"] == "move_next")
    assert move["changed_matches"] == 1
    assert move["shifted_minutes"] == 0
    assert move["conflicts"] == 0


def test_busy_alternative_pitch_is_not_offered():
    rows = [
        m(1, "2026-09-01T10:30:00", 1, 1, 2),
        m(2, "2026-09-01T11:00:00", 1, 3, 4),
        m(3, "2026-09-01T10:25:00", 2, 7, 8),
    ]
    options = compare_pitch_delay_recovery_options(
        rows,
        pitch_number=1,
        delay_minutes=10,
        now=datetime(2026, 9, 1, 10, 0),
        match_duration_minutes=20,
        pitch_break_minutes=0,
        rules=RULES,
        resolve_team_id=tid,
    )
    assert not any(o["kind"] == "move_next" for o in options)


def test_unresolved_do_nothing_is_not_recommended():
    rows = [
        m(1, "2026-09-01T10:30:00", 1, 1, 2),
        m(2, "2026-09-01T11:00:00", 1, 3, 4),
    ]
    options = compare_pitch_delay_recovery_options(
        rows,
        pitch_number=1,
        delay_minutes=10,
        now=datetime(2026, 9, 1, 10, 0),
        match_duration_minutes=20,
        pitch_break_minutes=0,
        rules=RULES,
        resolve_team_id=tid,
    )
    do_nothing = next(o for o in options if o["kind"] == "do_nothing")
    assert do_nothing["recommended"] is False
    assert do_nothing["unresolved_delay"] == 10
    assert options[0]["recommended"] is True


def test_ui_exposes_comparison_and_exact_preview_without_auto_apply():
    assert '"Jämför lösningar"' in APP
    assert 'st.markdown("### ✦ Autopilot jämför lösningar")' in APP
    assert '"Matcher som ändras"' in APP
    assert '"Lag som påverkas"' in APP
    assert '"Flyttade minuter"' in APP
    assert '"Visa exakt vad som skulle ändras"' in APP
    assert "Ingen lösning genomförs här." in APP
