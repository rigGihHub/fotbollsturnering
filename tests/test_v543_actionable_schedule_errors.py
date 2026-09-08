from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "cupnavi_core" / "schedule_workspace_view.py"
APP = ROOT / "app.py"
VERSION = ROOT / "VERSION.txt"


def _load_view():
    spec = importlib.util.spec_from_file_location("schedule_workspace_view_v543", VIEW)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_v543_version_is_synced():
    version = "2026.09.08-543-ACTIONABLE-SCHEDULE-ERRORS"
    assert VERSION.read_text().strip() == version
    assert version in APP.read_text()
    assert version in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_issue_match_numbers_extract_single_and_pair():
    module = _load_view()
    assert module.schedule_issue_match_numbers("Match 4 har en ogiltig plan.") == [4]
    assert module.schedule_issue_match_numbers("Plankrock mellan match 4 och match 9.") == [4, 9]
    assert module.schedule_issue_match_numbers("Ett lag är dubbelbokat i match 2 och match 2.") == [2]


def test_actionable_error_cards_open_manual_editor():
    text = VIEW.read_text()
    assert 'f"Rätta match {_match_number} →"' in text
    assert 'st.session_state[f"manual_schedule_edit_open_{tid}"] = True' in text
    assert 'st.session_state[f"manual_schedule_match_{tid}"] = match_id' in text
    assert 'expanded=bool(st.session_state.get(f"manual_schedule_edit_open_{tid}", False))' in text
    assert "schedule_issue_guidance(issue)" in text
    assert "Alla fel visas här." in text
