from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
SETUP=(ROOT/'cupnavi_core'/'initial_setup_view.py').read_text(encoding='utf-8')
MIG=(ROOT/'cupnavi_core'/'migrations.py').read_text(encoding='utf-8')

def test_group_flow_is_guided():
    assert 'st.markdown("### Skapa grupper")' in APP
    assert 'CupNavis förslag' in APP
    assert 'Jag vill skapa grupper manuellt' in APP
    assert 'Fortsätt till Schema →' in APP

def test_pitch_timing_mode_is_user_visible_and_persisted():
    assert 'Kräv samma avsparkstider på alla planer' in SETUP
    assert 'synchronized_pitch_times' in SETUP
    assert 'Samma avsparkstider på alla planer' in APP

def test_pitch_timing_mode_changes_scheduler_and_schema():
    assert 'synchronized_pitch_times = bool' in APP
    assert 'synchronized_slot_minutes' in APP
    assert 'LATEST_SCHEMA_VERSION = 27' in MIG
    assert 'pitch_timing_mode_v353' in MIG
