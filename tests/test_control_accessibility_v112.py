from pathlib import Path
from cupnavi_core.fairness import fairness_report
from cupnavi_core.migrations import LATEST_SCHEMA_VERSION
from cupnavi_core.i18n import text_direction


def app_text():
    return Path('app.py').read_text(encoding='utf-8')


def test_schema_v12_has_optional_control_and_info_features():
    text = Path('cupnavi_core/migrations.py').read_text(encoding='utf-8')
    assert LATEST_SCHEMA_VERSION >= 12
    for field in ['enable_control_center','enable_scorer_leaderboard','enable_assist_leaderboard','enable_card_statistics','enable_medical_info','enable_lost_found','enable_accessibility_info']:
        assert field in text
    assert 'CREATE TABLE IF NOT EXISTS functionary_shifts' in text
    assert 'CREATE TABLE IF NOT EXISTS control_incidents' in text


def test_public_optional_sections_and_accessibility_controls_exist():
    text = app_text()
    assert 'Cup Control Center' in text
    assert 'Hög kontrast' in text
    assert 'Större text' in text
    assert 'min-height:44px' in text
    assert ':focus-visible' in text
    assert 'Medicinsk beredskap' in text
    assert 'Lost & found / hittegods' in text
    assert 'Tillgänglighet för besökare' in text
    assert 'Funktionärsschema' in text


def test_fairness_report_is_bounded_and_explains_result():
    matches = [
        {'home_team_id':1,'away_team_id':2,'scheduled_start':'2026-08-24T08:00:00','pitch_number':1},
        {'home_team_id':1,'away_team_id':3,'scheduled_start':'2026-08-24T09:00:00','pitch_number':2},
        {'home_team_id':2,'away_team_id':3,'scheduled_start':'2026-08-24T12:00:00','pitch_number':1},
    ]
    report = fairness_report(matches)
    assert 0 <= report['score'] <= 100
    assert report['findings']
    assert report['participants'] == 3


def test_i18n_has_future_rtl_direction_support():
    assert text_direction("sv-SE") == "ltr"
    assert text_direction("ar-SA") == "rtl"
