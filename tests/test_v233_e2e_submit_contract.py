from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")


def test_create_submit_uses_dom_click_not_force_click():
    start=E2E.index("def _submit_create_tournament_form")
    end=E2E.index("def wait_for_persisted_tournament",start)
    block=E2E[start:end]
    assert 'submit.evaluate("el => el.click()")' in block
    assert "submit.click(force=True)" not in block


def test_create_submit_reacquires_and_refills_form_before_retry():
    start=E2E.index("def _submit_create_tournament_form")
    end=E2E.index("def wait_for_persisted_tournament",start)
    block=E2E[start:end]
    assert "for attempt in range(attempts)" in block
    assert "_ensure_create_tournament_expander_open(page)" in block
    assert "name_input.input_value() != cup_name" in block
    assert 'place_input.input_value() != "Örebro"' in block


def test_create_flow_waits_for_acceptance_signal_before_long_persist_wait():
    start=E2E.index("def _submit_create_tournament_form")
    end=E2E.index("def wait_for_persisted_tournament",start)
    block=E2E[start:end]
    assert "_persisted_tournament_row(cup_name)" in block
    assert 'name="Fortsätt → Lägg till lag"' in block
    assert "submit was not accepted" in block
