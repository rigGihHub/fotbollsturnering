from pathlib import Path


def _src():
    return Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")


def test_v515_hides_optional_schedule_type_by_default():
    src = _src()
    assert 'st.expander("⚙️ Schematyp (valfritt)", expanded=False)' in src
    assert "De flesta kan lämna detta som det är" in src


def test_v515_manual_edit_remains_available_but_not_in_primary_flow():
    src = _src()
    assert 'st.expander("✏️ Redigera befintligt schema manuellt", expanded=False)' in src


def test_v515_blocked_generator_has_no_dead_primary_button():
    src = _src()
    assert "if not create_disabled:" in src
    assert "show the problem and direct routes instead of a dead button" in src

def test_v515_timing_copy_points_to_current_control():
    src = _src()
    assert "Schematyp (valfritt)" in src
    assert "Ändra detta under cupens grundinställningar" not in src
