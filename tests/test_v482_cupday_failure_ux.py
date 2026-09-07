from pathlib import Path

VERSION = "2026.09.07-520-UNIQUE-PUBLICATION-CHECKLIST-KEYS"
APP = Path("app.py").read_text(encoding="utf-8")
REPORTER = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")


def test_version_is_v482():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_failure_message_is_actionable_and_prevents_double_tap():
    assert "CupNavi kunde inte bekräfta att ändringen sparades" in REPORTER
    assert "Tryck inte igen direkt" in REPORTER
    assert "Ladda om matchen" in REPORTER
    assert "inte registrera den en gång till" in REPORTER


def test_quick_result_write_is_guarded():
    start = REPORTER.index("def _save_quick_result_callback(")
    end = REPORTER.index("def _set_match_status_callback(", start)
    block = REPORTER[start:end]
    assert "except Exception:" in block
    assert "_set_write_failure_notice(" in block


def test_match_status_write_is_guarded():
    start = REPORTER.index("def _set_match_status_callback(")
    end = REPORTER.index("def _render_match_event_entry(", start)
    block = REPORTER[start:end]
    assert "except Exception:" in block
    assert "_set_write_failure_notice(" in block


def test_event_and_live_goal_writes_are_guarded():
    assert REPORTER.count("_set_write_failure_notice(") >= 7
    assert "deps.save_live_goal(" in REPORTER
    assert "deps.undo_live_goal(" in REPORTER
    assert "deps.save_event_rows(" in REPORTER


def test_bulk_result_write_is_guarded():
    marker = "outcome = deps.save_bulk_results(tournament_id, original_by_id, updates)"
    idx = REPORTER.index(marker)
    nearby = REPORTER[max(0, idx-400):idx+500]
    assert "try:" in nearby
    assert "except Exception:" in nearby
    assert "_set_write_failure_notice(" in nearby


def test_failure_notice_is_shown_before_success_message():
    fail = REPORTER.index('_write_failure_message = st.session_state.get("reporter_write_failure_message")')
    success = REPORTER.index('if "reporter_result_message" in st.session_state:')
    assert fail < success
