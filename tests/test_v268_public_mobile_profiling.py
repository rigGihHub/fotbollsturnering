from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
MODULE = (ROOT / "cupnavi_core" / "public_match_overview.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")


def test_v268_version_and_pure_public_overview_module():
    assert VERSION == "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"
    assert "import streamlit" not in MODULE
    assert "SELECT " not in MODULE
    assert "build_live_feed_html" in MODULE
    assert "build_highlights_html" in MODULE
    assert "build_summary_html" in MODULE


def test_public_match_fragment_records_stage_timings():
    for key in (
        'live_feed_ms', 'highlights_ms', 'visitors_ms', 'summary_share_ms',
        'filters_ms', 'events_ms', 'cards_weather_ms',
    ):
        assert f'stage_timings["{key}"]' in MATCHES
    assert '_cupnavi_public_matches_perf_history' in MATCHES
    assert 'Turneringsvy / Matcher – delsteg' in APP
