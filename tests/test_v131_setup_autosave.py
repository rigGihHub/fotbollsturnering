from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
MIG = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
ABOUT = Path("cupnavi_core/about.py").read_text(encoding="utf-8")
INFO = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
SETUP = Path("cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")

def test_v131_schema_and_version():
    assert 'APP_BUILD_VERSION = ' in APP
    assert Path('VERSION.txt').read_text(encoding='utf-8').strip() in APP
    assert 'LATEST_SCHEMA_VERSION = ' in MIG
    import re
    assert int(re.search(r'LATEST_SCHEMA_VERSION = (\d+)', MIG).group(1)) >= 17
    assert 'tournament_day_windows' in MIG
    assert 'difficulty TEXT' in MIG
    assert 'changing_rooms_available' in MIG
    assert 'show_price_information' in MIG

def test_competition_difficulty_levels_are_available():
    for label in ['Lätt','Medel','Svår','Extra svår']:
        assert label in APP + SETUP
    assert 'difficulty' in APP + SETUP

def test_daily_windows_are_required_and_used_by_scheduler():
    assert 'pitch_day_windows' in APP
    assert 'def pitch_bounds(day,pitch)' in APP
    assert 'valid_pitch_start_for' in APP
    assert 'validation_windows' in APP

def test_changing_rooms_and_prices_can_be_public():
    assert 'Tillgång till omklädningsrum' in SETUP
    assert 'Visa priser/avgifter publikt' in SETUP
    assert 'Priser/avgifter' in APP + INFO
    assert 'Omklädningsrum:' in INFO

def test_regular_settings_autosave_without_save_button():
    block = SETUP
    assert 'Spara upplägg' not in block
    assert '_autosave_tournament_field' in block
    assert '_autosave_rule_field' in block
    assert 'Fortsätt till Admin' in block

def test_about_page_catalog_tracks_new_capabilities():
    assert 'competition_difficulty' in ABOUT
    assert 'daily_venue_windows' in ABOUT
    assert 'practical_info' in ABOUT
