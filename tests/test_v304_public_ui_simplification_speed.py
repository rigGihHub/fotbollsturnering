from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text()
OVERVIEW = (ROOT / "cupnavi_core" / "public_match_overview.py").read_text()
FILTERS = (ROOT / "cupnavi_core" / "public_match_filters_view.py").read_text()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text()
VERSION = (ROOT / "VERSION.txt").read_text().strip()


def test_release_version_is_v304():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"


def test_matches_page_avoids_secondary_overview_db_and_highlight_work():
    assert "overview_snapshot(" not in MATCHES
    assert "snapshot_table_bundle(" not in MATCHES
    assert "competition_highlights(" not in MATCHES
    assert 'stage_timings["overview_db_ms"] = 0.0' in MATCHES
    assert 'stage_timings["highlights_ms"] = 0.0' in MATCHES
    assert "overview_snapshot=public_match_overview_db_snapshot" not in WORKSPACE


def test_matches_summary_is_compact_and_uses_already_loaded_data_only():
    assert "team_count" in OVERVIEW
    assert "played_count" in OVERVIEW
    assert "total_matches" in OVERVIEW
    assert "total_score" in OVERVIEW
    summary = OVERVIEW[OVERVIEW.index("def build_summary_html"):]
    assert "active_visitors" not in summary
    assert "highlights_html" not in summary
    assert "Besökare nu" not in summary


def test_weather_is_hidden_with_advanced_filter_controls():
    assert 'st.expander("Filter & visning", expanded=False)' in FILTERS
    expander_pos = FILTERS.index('st.expander("Filter & visning", expanded=False)')
    weather_pos = FILTERS.index('tr("Visa väderprognos")')
    return_pos = FILTERS.index("    return (")
    assert expander_pos < weather_pos < return_pos
    assert "show_weather," in FILTERS
    assert "show_match_weather = st.toggle" not in MATCHES
