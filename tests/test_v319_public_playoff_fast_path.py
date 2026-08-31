from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text()
VERSION = (ROOT / "VERSION.txt").read_text().strip()


def test_v319_version():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"


def test_existing_brackets_are_loaded_before_setup_validation():
    brackets_pos = VIEW.index("brackets, duplicate_brackets = brackets_for_display(tournament_id)")
    guard_pos = VIEW.index("if not brackets:", brackets_pos)
    specs_pos = VIEW.index("playoff_specs, playoff_setup_error = playoff_specs_for_tournament", guard_pos)
    assert brackets_pos < guard_pos < specs_pos


def test_setup_validation_is_guarded_by_missing_brackets():
    fragment = VIEW[VIEW.index("brackets, duplicate_brackets = brackets_for_display(tournament_id)"):]
    before_loop = fragment.split("for bracket in brackets:", 1)[0]
    assert "if not brackets:" in before_loop
    assert "playoff_specs_for_tournament" in before_loop


def test_duplicate_warning_and_bracket_rendering_are_preserved():
    assert 'st.warning("Äldre dubbletter av slutspel finns. Arrangören behöver regenerera schemat.")' in VIEW
    assert "for bracket in brackets:" in VIEW
    assert "render_bracket_tree(bracket[\"id\"], public=True" in VIEW
