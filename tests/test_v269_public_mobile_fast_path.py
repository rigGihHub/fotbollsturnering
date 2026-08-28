from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v269_version_and_weather_is_opt_in():
    assert VERSION == "2026.08.28-270-INCREMENTAL-PUBLIC-MATCHES"
    weather_block = APP[APP.index('show_match_weather = st.toggle('):]
    weather_block = weather_block[:500]
    assert 'value=False' in weather_block


def test_public_match_overview_uses_single_batched_sql_snapshot():
    start = APP.index('def public_match_overview_db_snapshot(')
    end = APP.index('def render_public_share_control', start)
    block = APP[start:end]
    assert 'WITH agg AS (' in block
    assert block.count('con.execute(') == 1
    assert 'visitor_sessions' in block
    assert 'scorer AS (' in block
    assert 'assister AS (' in block


def test_public_match_profiler_exposes_overview_db_stage():
    assert '_stage_timings["overview_db_ms"]' in APP
    assert '"Översikt DB": row.get("overview_db_ms", 0)' in APP
