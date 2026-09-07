from pathlib import Path

VERSION = "2026.09.07-493-BUTTON-LATENCY-IV"
APP = Path("app.py").read_text(encoding="utf-8")
ROLE_VIEW = Path("cupnavi_core/admin_role_codes_view.py").read_text(encoding="utf-8")
CONTRACT = Path("scripts/check_performance_contract.py").read_text(encoding="utf-8")


def test_version_is_v458():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_language_switch_uses_single_normal_rerun():
    start = APP.index("language_options =")
    end = APP.index("_install_streamlit_translation_hooks()", start)
    block = APP[start:end]
    assert "on_change=_sync_language_selector" in block
    assert "st.rerun()" not in block


def test_admin_entry_navigation_uses_callbacks():
    assert APP.count("on_click=_set_admin_entry_mode") >= 6
    assert "on_click=_open_admin_entry_tournament" in APP

    for key in (
        "admin_entry_create_v426",
        "admin_entry_manage_v426",
        "admin_entry_create_back_v426",
        "admin_manage_empty_back_v426",
        "admin_manage_empty_create_v426",
        "admin_manage_back_v426",
        "admin_manage_open_v426",
    ):
        pos = APP.index(key)
        nearby = APP[max(0, pos - 320):pos + 420]
        assert "st.rerun()" not in nearby


def test_open_admin_tournament_callback_sets_all_required_state():
    helper = APP[APP.index("def _open_admin_entry_tournament"):APP.index("# v426:", APP.index("def _open_admin_entry_tournament"))]
    assert 'st.session_state["preferred_tournament_id"]' in helper
    assert 'st.session_state["active_tournament_selector"]' in helper
    assert 'st.session_state["admin_manage_tournament_confirmed"] = True' in helper


def test_role_code_generation_does_not_force_second_rerun():
    block = ROLE_VIEW[ROLE_VIEW.index("if create_requested:"):ROLE_VIEW.index("if st.session_state.get(code_key):")]
    assert "rotate_code(table_name)" in block
    assert "st.rerun()" not in block


def test_app_explicit_rerun_count_is_reduced():
    assert APP.count("st.rerun()") <= 94


def test_existing_high_frequency_reporter_fast_paths_remain_guarded():
    assert "on_click=_adjust_quick_score" in CONTRACT
    assert "on_click=_save_quick_result_callback" in CONTRACT
    assert "on_click=_set_match_status_callback" in CONTRACT
