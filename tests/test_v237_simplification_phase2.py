
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_cup_settings_primary_action_is_visible_before_advanced_detail():
    block=_block('if admin_page == "Cupinställningar":','if admin_page == "Kontroller":')
    action=block.index('st.button("Ändra cupens inställningar"')
    consequence=block.index('with st.expander("Kontrollera konsekvens före större ändring"')
    assert action < consequence
    assert 'with st.expander("Teknisk release-status", expanded=False)' in block


def test_schedule_rule_and_quality_detail_is_collapsed():
    block=_block('if admin_page == "Skapa och publicera schema":','if admin_page == "Tabeller":')
    assert 'with st.expander("Regelverk & schemakvalitet", expanded=False)' in block
    assert 'st.markdown("#### Skapa eller uppdatera schema")' in block


def test_schedule_secondary_tools_are_progressively_disclosed():
    block=_block('if admin_page == "Skapa och publicera schema":','if admin_page == "Tabeller":')
    for label in [
        'with st.expander("Detaljer per grupp", expanded=False)',
        'with st.expander("Exportera schema", expanded=False)',
        'with st.expander("Reseinformation", expanded=False)',
    ]:
        assert label in block


def test_schedule_core_generation_action_remains_primary():
    block=_block('if admin_page == "Skapa och publicera schema":','if admin_page == "Tabeller":')
    assert 'if st.button(schedule_button_label, type="primary"' in block
    assert "create_all_group_matches(tid)" in block
    assert "generate_schedule(tid, tournament, rules" in block
