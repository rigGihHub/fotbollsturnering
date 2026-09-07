from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"


def test_v493_version_is_consistent():
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION


def test_v493_explicit_rerun_budget_is_77():
    assert APP.count("st.rerun()") == 77


def test_v493_state_only_team_navigation_is_callback_first():
    block = APP[APP.index('if admin_page == "Lag":'):APP.index('if admin_page == "Grupper":')]
    assert 'key=f"teams_back_to_setup_{tid}"' in block
    assert 'on_click=_set_session_state_values' in block
    assert 'key=f"change_team_limit_{tid}"' in block
    assert 'on_click=_set_admin_page' in block
    assert 'key=f"go_manage_classes_{tid}"' in block


def test_v493_confirmation_flags_are_callback_first():
    assert 'key=f"request_regenerate_all_team_codes_{tid}"' in APP
    assert 'on_click=_pop_session_state_key' in APP
    assert 'offer_confirm_key = f"confirm_delete_offer_{offer[\'id\']}"' in APP
