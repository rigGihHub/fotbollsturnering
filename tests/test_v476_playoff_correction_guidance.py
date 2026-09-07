from pathlib import Path
from cupnavi_core.playoff_dependency_safety import build_dependency_guidance

VERSION = "2026.09.07-494-PUBLIC-UX-PDF"
APP = Path("app.py").read_text(encoding="utf-8")
SCHEDULE = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")


def _value(row, key, default=None):
    return row.get(key, default)


def test_version_is_v476():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_guidance_names_locked_match_and_action():
    rows = [{
        "id": 42,
        "stage": "Semifinal",
        "match_no": 2,
        "scheduled_start": "2026-09-05T14:30:00",
        "match_status": "live",
        "home_score": 1,
        "away_score": 0,
        "event_count": 2,
    }]
    messages = build_dependency_guidance(rows, row_value=_value)
    assert len(messages) == 1
    msg = messages[0]
    assert "Semifinal #2 (match 42)" in msg
    assert "matchen har startat" in msg
    assert "resultat finns" in msg
    assert "matchhändelser finns" in msg
    assert "Återställ eller rätta den här matchen först" in msg


def test_guidance_works_with_result_without_status():
    rows = [{
        "id": 11,
        "stage": "Final",
        "match_no": 1,
        "scheduled_start": "",
        "match_status": "not_started",
        "home_score": 0,
        "away_score": 0,
        "event_count": 0,
    }]
    msg = build_dependency_guidance(rows, row_value=_value)[0]
    assert "Final #1 (match 11)" in msg
    assert "resultat finns" in msg


def test_guard_returns_guidance_and_enriched_message():
    start = APP.index("def _playoff_dependency_guard(")
    end = APP.index("def update_match_result_if_unchanged(", start)
    block = APP[start:end]
    assert "build_dependency_guidance(" in block
    assert '"guidance": guidance' in block
    assert "message = message + " in block


def test_reporter_bulk_uses_concrete_dependency_message():
    assert "first_dependency_message" in APP
    assert "dependency_message" in APP


def test_schedule_ui_surfaces_dependency_block():
    assert 'dependency_blocked = list(save_result.get("dependency_blocked", []))' in SCHEDULE
    assert "slutspelsresultat sparades inte eftersom en senare match redan används" in SCHEDULE
    assert "st.caption(_message)" in SCHEDULE
