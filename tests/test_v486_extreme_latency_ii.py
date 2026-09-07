from pathlib import Path

VERSION = "2026.09.07-507-REVIEWED-DOCUMENT-SCHEDULE-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
REPORTER = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")


def test_version_is_v486():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_reporter_rerun_budget_is_reduced():
    assert REPORTER.count("st.rerun()") <= 3


def test_undo_is_callback_driven():
    assert "def _undo_latest_quick_event()" in REPORTER
    assert "on_click=_undo_latest_quick_event" in REPORTER


def test_bulk_results_are_truly_lazy():
    assert "_show_bulk_results = st.toggle(" in REPORTER
    assert "if _show_bulk_results:" in REPORTER
    assert "# v486: truly lazy." in REPORTER


def test_recovery_clear_is_callback_driven():
    assert "def _clear_write_failure_notice()" in REPORTER
    assert "on_click=_clear_write_failure_notice" in REPORTER


def test_referee_ack_is_callback_driven():
    assert "on_click=deps.acknowledge_referee" in REPORTER


def test_cupday_start_uses_status_callback():
    assert '"▶ Starta match"' in APP
    assert "on_click=_cupday_set_match_status_callback" in APP


def test_app_rerun_budget_does_not_regress():
    assert APP.count("st.rerun()") <= 89
