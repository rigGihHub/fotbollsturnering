from pathlib import Path

from cupnavi_core.performance import PERFORMANCE_BUDGETS

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
CONTRACT = Path("scripts/check_performance_contract.py").read_text(encoding="utf-8")


def test_version_is_v457():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_high_frequency_public_budget_is_tighter():
    assert PERFORMANCE_BUDGETS["Turneringsvy/Mitt lag"]["warm_rerun"] == {
        "render_ms": 850.0, "db_calls": 2
    }


def test_admin_overview_warm_budget_is_tighter():
    assert PERFORMANCE_BUDGETS["Admin/Adminöversikt"]["warm_rerun"] == {
        "render_ms": 1050.0, "db_calls": 3
    }


def test_mobile_buttons_and_form_controls_have_44px_touch_targets():
    assert 'min-height:44px!important' in STYLE
    assert '[data-baseweb="select"] > div' in STYLE
    assert '[data-testid="stTextInput"] input' in STYLE
    assert '[data-testid="stNumberInput"] input' in STYLE
    assert '[data-testid="stCheckbox"] label' in STYLE
    assert '[data-testid="stRadio"] label' in STYLE


def test_mobile_expanders_are_touchable():
    assert '[data-testid="stExpander"] summary{min-height:44px!important}' in STYLE


def test_public_mobile_long_names_cannot_force_horizontal_overflow():
    assert '.cn-follow-team{font-size:1.22rem;overflow-wrap:anywhere}' in STYLE
    assert '.cn-next-meta,.cn-live-subtitle,.cn-live-teams,.public-team-name{overflow-wrap:anywhere}' in STYLE


def test_performance_contract_still_guards_public_mobile_fast_paths():
    assert "Mobile playoff must not add DB roundtrips" in CONTRACT
    assert "public_core_snapshot" in CONTRACT
