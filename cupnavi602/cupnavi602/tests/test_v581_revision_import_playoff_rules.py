from datetime import timedelta
from pathlib import Path

from cupnavi_core.revision_import import explicit_values, normalize_tie_rule, revision_summary
from cupnavi_core.schedule_domain import build_schedule_window

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
MIGRATIONS = (ROOT / 'cupnavi_core' / 'migrations.py').read_text(encoding='utf-8')
AI_IMPORT = (ROOT / 'cupnavi_core' / 'ai_cup_document_import.py').read_text(encoding='utf-8')
VER = (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_v581_version_and_revision_import_is_review_first():
    assert '581-REVISION-IMPORT-AND-PLAYOFF-RULES' in VER
    assert '🔄 Ny eller ändrad PDF / foto' in APP
    assert 'Jämför det nya underlaget med cupen' in APP
    assert '✓ Tillämpa valda ändringar' in APP
    assert 'CupNavi har inte flyttat några matcher automatiskt' in APP
    assert 'revision_pending' in APP and 'revision_applied' in APP


def test_revised_document_extraction_supports_pitch_and_playoff_specific_rules():
    assert "'pitch_windows'" in AI_IMPORT
    assert "'playoff_rule_values'" in AI_IMPORT
    assert 'Skilj på gruppspelets rule_values och playoff_rule_values' in AI_IMPORT
    assert 'Gissa aldrig' in AI_IMPORT


def test_playoff_can_have_own_match_duration_and_falls_back_to_group_rules():
    tournament = {
        'start_date': '2026-09-12', 'end_date': '2026-09-12',
        'playoff_tie_rule': 'Straffar direkt', 'extra_time_minutes': 0,
    }
    rules = {
        'first_match_time': '09:00', 'latest_kickoff_time': '18:00',
        'halves': 1, 'minutes_per_half': 25, 'halftime_minutes': 0,
        'playoff_halves': 2, 'playoff_minutes_per_half': 20, 'playoff_halftime_minutes': 5,
    }
    window = build_schedule_window(tournament, rules)
    assert window.duration_for_stage('Gruppspel') == timedelta(minutes=25)
    assert window.duration_for_stage('Semifinal') == timedelta(minutes=45)

    rules.update(playoff_halves=None, playoff_minutes_per_half=None, playoff_halftime_minutes=None)
    fallback = build_schedule_window(tournament, rules)
    assert fallback.duration_for_stage('Final') == timedelta(minutes=25)


def test_v36_persists_playoff_timing_overrides():
    assert 'LATEST_SCHEMA_VERSION = 36' in MIGRATIONS
    for field in ('playoff_halves', 'playoff_minutes_per_half', 'playoff_halftime_minutes', 'playoff_pitch_break_minutes'):
        assert field in MIGRATIONS
        assert field in APP


def test_revision_helpers_only_use_explicit_values_and_normalize_tie_rules():
    payload = {
        'rule_values': {'halves': 2, 'minutes_per_half': None},
        'playoff_rule_values': {'tie_rule': 'Förlängning och straffar', 'halves': 2},
        'pitch_windows': [{'venue': 'Plan 1'}],
        'matches': [{}], 'playoff_matches': [{}, {}], 'warnings': ['kontrollera'],
    }
    assert explicit_values(payload, 'rule_values') == {'halves': 2}
    assert normalize_tie_rule('Förlängning och straffar') == 'Förlängning + straffar'
    summary = revision_summary(payload)
    assert summary['group_rule_count'] == 1
    assert summary['playoff_rule_count'] == 2
    assert summary['pitch_window_count'] == 1
    assert summary['match_count'] == 1 and summary['playoff_match_count'] == 2


def test_kit_verification_status_is_admin_only_and_home_away_are_side_by_side():
    admin_start = APP.index('if admin_page == "Tröj setup":')
    groups_start = APP.index('if admin_page == "Grupper":', admin_start)
    kit_admin = APP[admin_start:groups_start]
    assert 'home_col, away_col = st.columns(2)' in kit_admin
    assert 'Verifierad källa' in kit_admin
    # The verification wording is not part of the public kit rendering helpers or public page source.
    assert APP.count('Verifierad källa') == 2
