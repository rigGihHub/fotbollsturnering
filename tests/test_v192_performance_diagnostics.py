from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_render_timer_starts_near_imports():
    assert "_APP_RENDER_STARTED = time.perf_counter()" in APP

def test_performance_panel_is_admin_overview_only():
    assert 'if view_mode == "Admin" and admin_page == "Adminöversikt":' in APP
    assert 'with st.expander("Prestandadiagnostik", expanded=False):' in APP

def test_performance_panel_reports_core_metrics():
    for token in [
        '"Render ms"', '"DB ms"', '"DB-anrop"', '"DB-andel %"',
        '"_cupnavi_perf_history"', 'metric("Render"', 'metric("Databas"',
    ]:
        assert token in APP
