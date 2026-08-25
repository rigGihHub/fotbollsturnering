from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_matches_are_isolated_in_fragment():
    public=APP[APP.index("def render_public_view"):APP.index("def render_match_reporter_view")]
    assert "@st.fragment" in public
    assert "def render_public_matches_fragment" in public
    assert "render_public_matches_fragment()" in public

def test_match_filters_and_weather_live_inside_fragment():
    public=APP[APP.index("def render_public_view"):APP.index("def render_match_reporter_view")]
    start=public.index("def render_public_matches_fragment")
    end=public.index("\n\n        render_public_matches_fragment()", start)
    frag=public[start:end]
    assert "st.segmented_control(" in frag
    assert "_filter_public_matches(" in frag
    assert 'st.toggle(' in frag
    assert "_render_public_match_cards(" in frag

def test_public_section_timings_are_recorded_per_session():
    for key in ("_public_perf_matches_", "_public_perf_stats_", "_public_perf_info_"):
        assert key in APP
    assert '"render_ms"' in APP
    assert '"db_calls"' in APP
    assert '"db_ms"' in APP

def test_admin_performance_panel_shows_both_cache_types():
    assert 'pc3.metric("SQL-cache"' in APP
    assert 'pc4.metric("Beräkningscache"' in APP
