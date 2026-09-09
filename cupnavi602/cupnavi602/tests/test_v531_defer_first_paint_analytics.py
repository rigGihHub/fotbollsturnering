from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")

def test_public_analytics_is_deferred_past_first_paint():
    start = APP.index("def track_public_visit(tournament_id):")
    end = APP.index("def public_match_overview_db_snapshot", start)
    fn = APP[start:end]
    assert "_cupnavi_visit_first_paint_seen_" in fn
    assert "st.session_state[first_paint_key] = True" in fn
    assert fn.index("return") < fn.index("run(")
    assert "precision-vs-latency" in fn

def test_version_is_v531():
    assert 'APP_BUILD_VERSION = "2026.09.08-531-DEFER-FIRST-PAINT-ANALYTICS"' in APP
