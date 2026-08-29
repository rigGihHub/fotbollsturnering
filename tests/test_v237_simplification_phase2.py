
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCHEDULE_VIEW=(ROOT/"cupnavi_core"/"schedule_workspace_view.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_cup_settings_primary_action_is_visible_before_advanced_detail():
    block=_block('if admin_page == "Cupinställningar":','if admin_page == "Kontroller":')
    action=block.index('st.button("Ändra cupens inställningar"')
    consequence=block.index('st.toggle("Kontrollera konsekvens före större ändring"')
    assert action < consequence
    assert 'with st.expander("Teknisk release-status", expanded=False)' in block


def test_schedule_rule_and_quality_detail_is_collapsed():
    block=SCHEDULE_VIEW
    assert '"Visa regelverk & schemakvalitet"' in block
    assert '_show_schedule_quality = st.toggle(' in block
    assert 'st.markdown("#### Skapa eller uppdatera schema")' in block


def test_schedule_secondary_tools_are_progressively_disclosed():
    block=SCHEDULE_VIEW
    for label in [
        'with st.expander("Detaljer per grupp", expanded=False)',
        '_show_schedule_export = st.toggle("Exportera schema"',
        '_show_schedule_travel = st.toggle("Reseinformation"',
    ]:
        assert label in block


def test_schedule_core_generation_action_remains_primary():
    block=SCHEDULE_VIEW
    assert 'if st.button(schedule_button_label, type="primary"' in block
    assert "create_all_group_matches(tid)" in block
    assert "generate_schedule(tid, tournament, rules" in block
