from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_set_admin_page_syncs_guided_flow_widgets():
    assert 'st.session_state[f"admin_flow_{tid}"] = step_name' in APP
    assert 'st.session_state[f"admin_flow_page_{tid}_{step_name}"] = page' in APP


def test_teams_continue_button_still_targets_groups():
    marker = '"Fortsätt till Grupper →"'
    pos = APP.index(marker)
    nearby = APP[pos:pos + 500]
    assert 'on_click=_set_admin_page' in nearby
    assert 'args=("Grupper",)' in nearby
