from datetime import datetime
from pathlib import Path

from cupnavi_core.autopilot_recovery import compare_pitch_outage_recovery_options
from cupnavi_core.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _resolve(source):
    parts = str(source).split(":")
    return int(parts[1]) if len(parts) == 2 and parts[0] == "team" and parts[1].isdigit() else None


def test_release_version_and_note():
    assert APP_VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"
    assert (ROOT / "PITCH_OUTAGE_ASSIST_V410.md").exists()


def test_pitch_outage_can_redistribute_without_changing_times():
    matches = [
        {"id": 1, "scheduled_start": "2026-09-03T12:00", "pitch_number": 1, "home_source": "team:1", "away_source": "team:2", "home_score": None, "away_score": None},
        {"id": 2, "scheduled_start": "2026-09-03T12:50", "pitch_number": 1, "home_source": "team:3", "away_source": "team:4", "home_score": None, "away_score": None},
        {"id": 3, "scheduled_start": "2026-09-03T14:00", "pitch_number": 2, "home_source": "team:5", "away_source": "team:6", "home_score": None, "away_score": None},
    ]
    options = compare_pitch_outage_recovery_options(
        matches,
        pitch_number=1,
        now=datetime.fromisoformat("2026-09-03T11:00"),
        rules={},
        resolve_team_id=_resolve,
    )
    recommended = next(option for option in options if option["recommended"])
    assert recommended["kind"] == "redistribute_same_times"
    assert recommended["unresolved_count"] == 0
    assert {change["pitch_number"] for change in recommended["changes"]} == {2}
    assert [change["scheduled_start"] for change in recommended["changes"]] == ["2026-09-03T12:00", "2026-09-03T12:50"]


def test_pitch_outage_preview_is_read_only_and_exposed_on_cupday():
    source = (ROOT / "app.py").read_text()
    assert 'with st.expander("Plan ur spel? Jämför lösningar"' in source
    assert "compare_pitch_outage_recovery_options(" in source
    assert "Förhandsvisningen ändrar inget schema" in source
    block = source[source.index('with st.expander("Plan ur spel? Jämför lösningar"'):source.index("    if _day_autopilot:", source.index('with st.expander("Plan ur spel? Jämför lösningar"'))]
    assert "run(" not in block
    assert "all_rows(" not in block
    assert "one_row(" not in block
