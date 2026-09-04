from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
WIZARD = Path('cupnavi_core/new_tournament_wizard.py').read_text(encoding='utf-8')
SETUP = Path('cupnavi_core/initial_setup_view.py').read_text(encoding='utf-8')
PUBLIC = Path('cupnavi_core/public_workspace_view.py').read_text(encoding='utf-8')
VERSION = Path('VERSION.txt').read_text(encoding='utf-8').strip()


def test_release_version():
    assert VERSION == '2026.09.04-449-MOBILE-PLAYOFF-ACTION'


def test_admin_starts_with_clean_choice_gate():
    assert 'Vad vill du göra?' in APP
    assert 'Skapa ny cup' in APP
    assert 'Administrera befintlig cup' in APP
    assert 'st.session_state["admin_entry_mode"] = None' in APP
    assert 'st.session_state["admin_manage_tournament_confirmed"] = False' in APP


def test_no_result_manual_playoff_is_explicit_option():
    label = 'Spela utan resultat · skapa slutspel manuellt'
    assert label in WIZARD
    assert label in SETUP
    assert 'MANUAL_PLAYOFF_FORMAT = "Manuellt slutspel"' in APP
    assert 'if tournament["playoff_format"] == MANUAL_PLAYOFF_FORMAT' in APP


def test_manual_playoff_can_be_seeded_and_advanced_without_scores():
    assert 'Skapa manuellt slutspel' in APP
    assert 'Välj lag i seedningsordning' in APP
    assert 'Spara vinnare' in APP
    assert 'decided_winner_id' in APP
    assert 'an organiser may advance a team without' in APP
    assert '_manual_playoff' in PUBLIC


def test_planned_team_count_is_not_forced_twice_in_wizard():
    assert 'Lagantalet sparades när klassen lades till.' in WIZARD
    assert 'Ändra lagantal' in WIZARD
    # The primary class card no longer immediately asks for the same value again.
    assert 'st.markdown(f"**{competition_class_label(row)}** · {saved} planerade lag")' in WIZARD
