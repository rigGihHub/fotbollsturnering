from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.08.31-348-GUIDED-CUP-SETUP"


def test_admin_can_switch_tournament_without_sidebar():
    assert 'with st.expander(f"🏆 Turnering · {_tournament_selector_label(tid)}", expanded=False)' in APP
    assert '"Byt aktiv turnering"' in APP
    assert 'key="main_active_tournament_selector"' in APP
    assert 'on_change=_apply_main_tournament_selection' in APP


def test_main_switcher_syncs_canonical_selector_and_preference():
    start = APP.index("def _apply_main_tournament_selection")
    end = APP.index('if view_mode == "Admin":', start)
    block = APP[start:end]
    assert 'st.session_state["active_tournament_selector"] = selected_id' in block
    assert 'st.session_state["preferred_tournament_id"] = selected_id' in block
    assert "if selected_id not in tournament_ids" in block


def test_mobile_creation_path_is_still_available_next_to_switcher():
    switcher = APP.index('with st.expander(f"🏆 Turnering · {_tournament_selector_label(tid)}", expanded=False)')
    creator = APP.index('with st.expander("➕ Ny turnering", expanded=False)', switcher)
    assert creator > switcher
    assert 'render_new_tournament_creator(key_prefix="mobile_main")' in APP[creator:creator+500]
