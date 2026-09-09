from pathlib import Path

from cupnavi_core.performance import build_performance_snapshot, performance_log_line

APP = Path('app.py').read_text(encoding='utf-8')


def test_public_workspace_has_only_the_outer_fragment_boundary():
    assert '@st.fragment\ndef render_public_view' in APP
    assert '@st.fragment\ndef render_public_info_section' not in APP
    assert '@st.fragment\ndef render_public_statistics_section' not in APP


def test_performance_snapshot_classifies_route_and_first_render():
    snap=build_performance_snapshot(
        render_ms=1500.0,
        perf={'db_ms':300.0,'db_calls':4,'writes':1,'cache_hits':2,'derived_hits':3},
        view_mode='Turneringsvy', public_page='Matcher', run_seq=1,
    )
    assert snap['route']=='Turneringsvy/Matcher'
    assert snap['session_phase']=='first_render'
    assert snap['db_share_pct']==20.0
    assert snap['db_calls']==4


def test_structured_perf_logging_is_opt_in_and_route_history_exists():
    assert 'CUPNAVI_PERF_LOG' in APP
    assert 'performance_log_line(_perf_snapshot)' in APP
    assert '"_cupnavi_perf_route_history"' in APP
    line=performance_log_line({'route':'Admin/Schema','render_ms':10})
    assert line.startswith('CUPNAVI_PERF {')
    assert 'Admin/Schema' in line


def test_admin_diagnostics_show_recent_routes():
    assert '**Senaste rutter**' in APP
    assert '"Fas": row["session_phase"]' in APP
