from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "public_match_repository.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
FILTERS = (ROOT / "cupnavi_core" / "public_match_filters_view.py").read_text(encoding="utf-8")


def test_v269_version_and_weather_is_opt_in():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"
    weather_block = FILTERS[FILTERS.index('show_weather = st.toggle('):]
    weather_block = weather_block[:500]
    assert 'value=False' in weather_block
    assert 'Filter & visning' in FILTERS


def test_public_match_overview_uses_single_batched_sql_snapshot():
    assert 'WITH agg AS (' in REPO
    overview_block = REPO[REPO.index('def fetch_public_match_overview'):REPO.index('def fetch_public_match_events')]
    assert overview_block.count('con.execute(') == 1
    assert 'visitor_sessions' in REPO
    assert 'scorer AS (' in REPO
    assert 'assister AS (' in REPO
    start = APP.index('def public_match_overview_db_snapshot(')
    end = APP.index('def render_public_share_control', start)
    assert 'fetch_public_match_overview' in APP[start:end]

def test_public_match_profiler_exposes_overview_db_stage():
    assert 'stage_timings["overview_db_ms"]' in MATCHES
    assert '"Översikt DB": row.get("overview_db_ms", 0)' in APP
