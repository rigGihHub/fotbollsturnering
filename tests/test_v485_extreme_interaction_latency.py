from pathlib import Path

VERSION = "2026.09.07-524-PRIMARY-FLOW-PITCH-COUNT-FIX"
APP = Path("app.py").read_text(encoding="utf-8")
REPORTER = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")


def test_version_is_v485():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_cupday_status_buttons_use_callbacks():
    assert "def _cupday_set_match_status_callback" in APP
    for label in ["▶ Starta match", "⏸ Paus", "▶ Fortsätt", "■ Avsluta"]:
        idx=APP.index(label)
        nearby=APP[idx:idx+700]
        assert "on_click=_cupday_set_match_status_callback" in nearby
    assert APP.count("st.rerun()") <= 90


def test_reporter_quick_events_use_callbacks():
    assert "on_click=_apply_quick_event" in REPORTER
    assert "on_click=_save_live_goal_callback" in REPORTER
    assert REPORTER.count("st.rerun()") <= 13


def test_quick_event_callback_does_not_force_rerun():
    start=REPORTER.index("def _apply_quick_event")
    end=REPORTER.index("def _save_live_goal_callback", start)
    assert "st.rerun()" not in REPORTER[start:end]


def test_live_goal_callback_does_not_force_rerun():
    start=REPORTER.index("def _save_live_goal_callback")
    end=REPORTER.index("if match_status != MATCH_FINISHED", start)
    assert "st.rerun()" not in REPORTER[start:end]
