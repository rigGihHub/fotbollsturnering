
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")


def test_selector_helper_is_idempotent_for_current_value():
    start=E2E.index("def choose_streamlit_option")
    end=E2E.index("\ndef ",start+5)
    block=E2E[start:end]
    assert "if combo.input_value().strip() == option:" in block
    assert "return" in block
    assert 'get_by_role("option",name=option,exact=True)' in block


def test_active_tournament_regression_performs_real_b_to_a_switch():
    start=E2E.index("def test_active_tournament_switch_survives_browser_rerun")
    block=E2E[start:]
    first_b=block.index('choose_streamlit_option(page,"Aktiv turnering",second)')
    then_a=block.index('choose_streamlit_option(page,"Aktiv turnering",first)')
    reload_pos=block.index('page.reload(wait_until="domcontentloaded")')
    assert first_b < then_a < reload_pos
    assert 'input_value() == second' in block
    assert 'input_value() == first' in block


def test_reload_still_verifies_a_after_real_switch():
    start=E2E.index("def test_active_tournament_switch_survives_browser_rerun")
    block=E2E[start:]
    assert 'assert selector.input_value() == first' in block
    assert "canonical cup query parameter" in block
