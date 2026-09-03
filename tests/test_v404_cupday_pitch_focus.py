from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_dashboard import build_cup_day_snapshot

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core/style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def _finished_without_score():
    return {
        "id": 44,
        "scheduled_start": "2026-09-03T10:00:00",
        "pitch_number": 2,
        "home_source": "team:1",
        "away_source": "team:2",
        "home_score": None,
        "away_score": None,
        "match_status": "finished",
    }


def test_version_and_release_note():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
    assert (ROOT / "CUPDAY_PITCH_FOCUS_V404.md").exists()


def test_result_counting_tournament_keeps_finished_match_without_score_actionable():
    snap = build_cup_day_snapshot(
        [_finished_without_score()],
        now=datetime(2026, 9, 3, 11, 0),
        require_results=True,
    )
    assert snap["completed"] == []
    assert [row["id"] for row in snap["reporting_due"]] == [44]


def test_result_free_matchcamp_can_finish_without_score():
    snap = build_cup_day_snapshot(
        [_finished_without_score()],
        now=datetime(2026, 9, 3, 11, 0),
        require_results=False,
    )
    assert [row["id"] for row in snap["completed"]] == [44]
    assert snap["reporting_due"] == []


def test_cupday_reuses_snapshot_for_visible_pitch_focus_without_new_query():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    focus = section[section.index('if _day_snapshot["pitch_states"]:'):section.index('# v403: distinguish a late kickoff')]
    assert 'Planer just nu' in focus
    assert 'cn-pitch-focus-grid' in focus
    assert '_day_snapshot["pitch_states"][:6]' in focus
    assert 'all_rows(' not in focus
    assert 'one_row(' not in focus
    assert 'Rapportera resultat / händelser' in section


def test_pitch_focus_is_mobile_responsive():
    assert '.cn-pitch-focus-grid{' in STYLE
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in STYLE
    assert '.cn-pitch-focus-grid{grid-template-columns:1fr}' in STYLE
