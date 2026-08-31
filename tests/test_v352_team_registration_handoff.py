from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
VERSION = Path("VERSION.txt").read_text(encoding="utf-8").strip()


def test_v352_release_version():
    assert VERSION == "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"


def test_team_page_starts_with_guided_primary_task():
    block = APP.split('if admin_page == "Lag":', 1)[1].split('if admin_page == "Grupper":', 1)[0]
    assert 'st.header("Lägg till lag")' in block
    assert '**① Lägg till lag** → ② Grupper → ③ Schema → ④ Kontroll → ⑤ Publicera' in block
    assert block.index('max_teams = int(tournament["expected_team_count"] or 0)') < block.index('with st.expander("Fler lagverktyg", expanded=False):')


def test_team_progress_and_handoff_are_explicit():
    assert 'av {max_teams} lag registrerade' in APP
    assert 'lag kvar. Lägg till' in APP
    assert 'Alla {registered_team_count} lag är registrerade' in APP
    assert '"Fortsätt → Skapa grupper"' in APP


def test_team_form_separates_required_and_optional_fields():
    assert '"Lagnamn *"' in APP
    assert '**Obligatoriskt:** lagnamn.' in APP
    assert 'with st.expander("Valfria laguppgifter", expanded=False):' in APP
    assert '"Lägg till laget"' in APP
