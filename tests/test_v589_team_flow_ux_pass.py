from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')


def _team_block():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Tröj setup":', start)
    return APP[start:end]


def test_team_page_has_one_clear_core_task_before_optional_tools():
    block = _team_block()
    assert 'När laglistan är klar går du vidare till Grupper. Allt annat på sidan är valfritt.' in block
    assert '### {\'Nästa lag\' if registered_team_count else \'Första laget\'}' in block
    assert '"Lägg till laget", type="primary"' in block
    assert '"Fortsätt till Grupper →",\n                type="primary"' in block


def test_kit_setup_no_longer_competes_at_top_of_team_step():
    block = _team_block()
    head = block[: block.index('st.markdown(\n        """<div class="cn-workspace-head">')]
    assert 'Tröj setup' not in head
    assert 'key=f"participant_kit_setup_{tid}"' in block
    assert 'if st.toggle("Fler lagverktyg"' in block


def test_optional_team_details_and_roster_import_are_progressively_disclosed():
    block = _team_block()
    assert 'with st.expander("Valfritt · komplettera laget senare", expanded=False):' in block
    assert 'with st.expander("Spelare från bild · valfritt", expanded=False):' in block


def test_registered_team_list_defaults_to_setup_relevant_fields_only():
    block = _team_block()
    section = block[block.index('st.subheader(f"Registrerade lag'):]
    first_table = section[: section.index('with st.expander("Visa kontakt- och resedetaljer"')]
    assert '"Lag": team_row["name"]' in first_table
    assert '"Tävlingsklass":' in first_table
    assert '"Grupp":' in first_table
    assert '"Telefon":' not in first_table
    assert '"E-post":' not in first_table
    assert 'with st.expander("Visa kontakt- och resedetaljer", expanded=False):' in section


def test_v589_version_is_synchronized():
    version = '2026.09.09-589-TEAM-FLOW-UX-PASS'
    assert version in APP
    assert (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip() == version
    assert version in (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')
