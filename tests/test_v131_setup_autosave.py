from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
MIG = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
ABOUT = Path("cupnavi_core/about.py").read_text(encoding="utf-8")

def test_v131_schema_and_version():
    assert '2026.08.24-131-SETUP-AUTOSAVE' in APP
    assert 'LATEST_SCHEMA_VERSION = 16' in MIG
    assert 'tournament_day_windows' in MIG
    assert 'difficulty TEXT' in MIG
    assert 'changing_rooms_available' in MIG
    assert 'show_price_information' in MIG

def test_competition_difficulty_levels_are_available():
    for label in ['Lätt','Medel','Svår','Extra svår']:
        assert label in APP
    assert 'difficulty' in APP

def test_daily_windows_are_required_and_used_by_scheduler():
    assert 'Bekräfta plantider för' in APP
    assert 'def day_bounds(day)' in APP
    assert 'daily_windows' in APP
    assert 'validation_windows' in APP

def test_changing_rooms_and_prices_can_be_public():
    assert 'Tillgång till omklädningsrum' in APP
    assert 'Visa priser/avgifter publikt' in APP
    assert 'Priser/avgifter' in APP
    assert 'Omklädningsrum:' in APP

def test_regular_settings_autosave_without_save_button():
    start = APP.index('def render_initial_tournament_setup')
    end = APP.index('def _render_with_friendly_error', start)
    block = APP[start:end]
    assert 'Spara upplägg' not in block
    assert '_autosave_tournament_field' in block
    assert '_autosave_rule_field' in block
    assert 'Fortsätt till Admin' in block

def test_about_page_catalog_tracks_new_capabilities():
    assert 'competition_difficulty' in ABOUT
    assert 'daily_venue_windows' in ABOUT
    assert 'practical_info' in ABOUT
