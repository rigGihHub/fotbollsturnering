from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
INFO=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STATS=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
MATCHES=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
WORKSPACE=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")

def test_matches_are_isolated_in_fragment():
    public=WORKSPACE
    assert "@st.fragment" in public
    assert "def render_public_matches_fragment" in public
    assert "render_public_matches_fragment()" in public

def test_match_filters_and_weather_live_inside_fragment():
    public=WORKSPACE
    assert "render_public_matches_fragment_module(" in public
    assert "st.segmented_control(" in MATCHES
    assert "filter_matches_view(" in MATCHES
    filters = Path('cupnavi_core/public_match_filters_view.py').read_text(encoding='utf-8')
    assert 'st.toggle(' in filters
    assert "render_match_cards(" in MATCHES

def test_public_section_timings_are_recorded_per_session():
    assert "_public_perf_matches_" in MATCHES
    assert "_public_perf_stats_" in STATS
    assert "_public_perf_info_" in INFO
    assert '"render_ms"' in MATCHES
    assert '"db_calls"' in MATCHES
    assert '"db_ms"' in MATCHES

def test_admin_performance_panel_shows_both_cache_types():
    assert 'pc3.metric("SQL-cache"' in APP
    assert 'pc4.metric("Beräkningscache"' in APP
