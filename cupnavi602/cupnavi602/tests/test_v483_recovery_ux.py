from pathlib import Path

VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"
APP = Path("app.py").read_text(encoding="utf-8")
REPORTER = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")


def test_version_is_v483():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_failure_context_is_persisted():
    assert '"reporter_write_failure_context"' in REPORTER
    assert '"operation": str(operation)' in REPORTER
    assert '"refreshed": False' in REPORTER


def test_refresh_action_exists_and_clears_server_cache():
    assert "🔄 Läs om från servern" in REPORTER
    assert "deps.refresh_server_state()" in REPORTER
    assert "refresh_server_state=_clear_render_query_cache" in APP


def test_quick_result_recovery_can_verify_already_saved():
    assert 'intended={"home_score": int(home_score), "away_score": int(away_score)}' in REPORTER
    assert "Ditt försök finns redan sparat" in REPORTER
    assert "registrera det inte igen" in REPORTER


def test_recovery_does_not_auto_retry_write():
    block = REPORTER[REPORTER.index("def _refresh_after_write_failure"):REPORTER.index("@dataclass", REPORTER.index("def _refresh_after_write_failure"))]
    assert "refresh_server_state" in block
    assert "save_quick_result" not in block
    assert "save_live_goal" not in block


def test_operator_must_explicitly_clear_recovery_state():
    assert "✓ Jag har kontrollerat serverläget" in REPORTER
    assert 'st.session_state.pop("reporter_write_failure_context", None)' in REPORTER
