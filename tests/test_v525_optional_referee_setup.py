from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIZARD = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text()
APP = (ROOT / "app.py").read_text()
OVERVIEW = (ROOT / "cupnavi_core" / "admin_overview.py").read_text()


def test_referee_choice_is_part_of_pitch_and_time_setup():
    assert 'st.markdown("**Domare**")' in WIZARD
    assert '"Lägg till domare nu", "Domare tillsätts senare"' in WIZARD
    assert "wizard_referee_timing_" in WIZARD


def test_later_mode_is_persisted_and_does_not_block_wizard():
    assert "UPDATE schedule_rules SET referee_mode='Senare'" in WIZARD
    assert "blockerar inte publicering" in WIZARD
    # wizard navigation remains gated only by pitch/time/address essentials
    assert 'nav(can_next=valid and unverified == 0 and _pitch_size != "Välj planstorlek")' in WIZARD


def test_later_mode_suppresses_missing_referee_attention():
    assert 'casefold() == "senare"' in OVERVIEW
    assert 'referee_mode=str(_row_value(sidebar_rules, "referee_mode", "Automatisk")' in APP


def test_referee_admin_page_can_switch_out_of_later_mode():
    assert '_ref_mode_options = ["Automatisk", "Manuell", "Senare"]' in APP
    assert 'Cupen kan fortsätta genom setupen och publiceras utan domare.' in APP
