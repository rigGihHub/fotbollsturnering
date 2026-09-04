from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WIZARD = (ROOT / "cupnavi_core/new_tournament_wizard.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v441_version_and_wizard_navigation_are_single_rerun():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert "def _set_wizard_step(target_step: int)" in WIZARD
    assert "on_click=_set_wizard_step" in WIZARD
    nav_block = WIZARD[WIZARD.index("def nav(*,"):WIZARD.index("arrangement_type =", WIZARD.index("def nav(*,"))]
    assert "st.rerun()" not in nav_block


def test_v441_rules_and_admin_guide_navigation_use_callbacks():
    assert "def _leave_rules_for_step(target_step: int)" in SETUP
    assert SETUP.count("on_click=_leave_rules_for_step") >= 3
    assert "def _open_admin_page(target_page: str)" in APP
    assert "on_click=_open_admin_page" in APP
    assert "args=(fairness_state_key, True)" in APP
