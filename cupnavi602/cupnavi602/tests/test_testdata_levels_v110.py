from pathlib import Path


def app_text():
    return Path('app.py').read_text(encoding='utf-8')


def test_progressive_testdata_levels_exist():
    text = app_text()
    for label in (
        'Halva gruppspelet',
        'Hela gruppspelet',
        'Halva slutspelet',
        'Hela cupen färdig',
    ):
        assert label in text
    assert 'def _demo_apply_progress_level(' in text
    assert 'def _demo_reset_results(' in text
    assert 'def _demo_prepare_schedule(' in text


def test_demo_data_covers_portal_contacts_and_public_features():
    text = app_text()
    assert 'participant_access_credentials' in text
    assert 'responsible_name' in text
    assert 'CupNavi Demo Partner' in text
    assert 'Alex Cupvärd' in text
    assert 'Demo Café' in text
    assert 'venue_points' in text
    assert 'Träningsmatch' in text
    assert 'age_classes_json' in text


def test_completed_demo_level_marks_tournament_completed():
    service = (Path('cupnavi_core') / 'demo_data_service.py').read_text(encoding='utf-8')
    assert "lifecycle_status='completed'" in service
    assert 'Democupen är färdigspelad' in service
