from pathlib import Path
from cupnavi_core.revision_import import analyze_match_revision_impacts

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VER = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def _m(mid, start, pitch, home, away, referee=None, phase="group"):
    return {"id": mid, "scheduled_start": start, "pitch_number": pitch, "home": home, "away": away, "referee_id": referee, "phase": phase}


def _sel(current, *, start=None, pitch=None):
    return {"current": current, "apply_start": start, "apply_pitch": pitch}


def test_v584_ui_has_consequence_gate_before_apply():
    assert "584-REVISION-CONSEQUENCE-PREVIEW" in VER
    assert "Konsekvenskontroll före godkännande" in APP
    assert "Välj alla tekniskt säkra" in APP
    assert 'not bool(_impact.get("can_apply", True))' in APP


def test_pitch_and_team_overlap_block_selected_change():
    current = [
        _m(1, "2026-09-12T09:00:00", 1, "A", "B"),
        _m(2, "2026-09-12T10:00:00", 1, "A", "C"),
    ]
    selected = [_sel(current[1], start="2026-09-12T09:10:00")]
    impact = analyze_match_revision_impacts(selected, current, group_duration_minutes=30, playoff_duration_minutes=30)
    codes = {x["code"] for x in impact["blockers"]}
    assert "pitch_overlap" in codes
    assert "team_overlap" in codes
    assert impact["can_apply"] is False


def test_referee_overlap_blocks_even_on_different_pitches():
    current = [
        _m(1, "2026-09-12T09:00:00", 1, "A", "B", referee=7),
        _m(2, "2026-09-12T10:00:00", 2, "C", "D", referee=7),
    ]
    selected = [_sel(current[1], start="2026-09-12T09:15:00")]
    impact = analyze_match_revision_impacts(selected, current, group_duration_minutes=30, playoff_duration_minutes=30)
    assert any(x["code"] == "referee_overlap" for x in impact["blockers"])


def test_confirmed_pitch_window_blocks_outside_availability():
    current = [_m(1, "2026-09-12T09:00:00", 1, "A", "B")]
    selected = [_sel(current[0], start="2026-09-12T08:30:00")]
    windows = [{"pitch_number": 1, "play_date": "2026-09-12", "start_time": "09:00", "end_time": "17:00", "confirmed": 1}]
    impact = analyze_match_revision_impacts(selected, current, group_duration_minutes=30, playoff_duration_minutes=30, pitch_windows=windows)
    assert any(x["code"] == "pitch_window" for x in impact["blockers"])


def test_short_rest_is_warning_not_hard_block():
    current = [
        _m(1, "2026-09-12T09:00:00", 1, "A", "B"),
        _m(2, "2026-09-12T10:30:00", 2, "A", "C"),
    ]
    selected = [_sel(current[1], start="2026-09-12T09:50:00")]
    impact = analyze_match_revision_impacts(selected, current, group_duration_minutes=30, playoff_duration_minutes=30, minimum_rest_minutes=45)
    assert impact["can_apply"] is True
    assert any(x["code"] == "short_rest" for x in impact["warnings"])


def test_collective_selected_changes_are_evaluated_together():
    current = [
        _m(1, "2026-09-12T09:00:00", 1, "A", "B"),
        _m(2, "2026-09-12T09:30:00", 1, "C", "D"),
    ]
    selected = [
        _sel(current[0], start="2026-09-12T10:00:00"),
        _sel(current[1], start="2026-09-12T10:30:00"),
    ]
    impact = analyze_match_revision_impacts(selected, current, group_duration_minutes=30, playoff_duration_minutes=30)
    assert impact["can_apply"] is True
    assert impact["blockers"] == []
