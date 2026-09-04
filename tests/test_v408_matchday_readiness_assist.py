from datetime import datetime, timedelta
from pathlib import Path

from cupnavi_core.cup_day_autopilot import build_matchday_readiness_advice
from cupnavi_core.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _match(now, *, minutes=10, referee_id=None, home='team:1', away='team:2'):
    return {
        'id': 10,
        'scheduled_start': (now + timedelta(minutes=minutes)).isoformat(timespec='minutes'),
        'pitch_number': 2,
        'home_source': home,
        'away_source': away,
        'home_score': None,
        'away_score': None,
        'referee_id': referee_id,
        'match_status': 'not_started',
    }


def test_version_and_release_note():
    assert APP_VERSION == '2026.09.04-449-MOBILE-PLAYOFF-ACTION'
    assert (ROOT / 'MATCHDAY_READINESS_ASSIST_V408.md').exists()


def test_unchecked_team_near_kickoff_is_flagged():
    now = datetime(2026, 9, 3, 10, 0)
    advice = build_matchday_readiness_advice(
        [_match(now, minutes=10, referee_id=5)],
        now=now,
        team_checkins={1: False, 2: True},
        checkin_enabled=True,
        referee_mode='Automatisk',
    )
    assert advice[0]['kind'] == 'team_not_checked_in'
    assert advice[0]['severity'] == 'error'
    assert advice[0]['action'] == 'open_team_checkin'


def test_missing_referee_is_only_flagged_in_automatic_mode():
    now = datetime(2026, 9, 3, 10, 0)
    row = _match(now, minutes=12, referee_id=None)
    auto = build_matchday_readiness_advice(
        [row], now=now, team_checkins={1: True, 2: True},
        checkin_enabled=True, referee_mode='Automatisk',
    )
    manual = build_matchday_readiness_advice(
        [row], now=now, team_checkins={1: True, 2: True},
        checkin_enabled=True, referee_mode='Manuell',
    )
    assert any(item['kind'] == 'missing_referee' for item in auto)
    assert not any(item['kind'] == 'missing_referee' for item in manual)


def test_unresolved_playoff_sources_are_not_guessed_as_missing_teams():
    now = datetime(2026, 9, 3, 10, 0)
    row = _match(now, home='winner:7', away='group:2:1', referee_id=3)
    advice = build_matchday_readiness_advice(
        [row], now=now, team_checkins={1: False, 2: False},
        checkin_enabled=True, referee_mode='Automatisk',
    )
    assert not any(item['kind'] == 'team_not_checked_in' for item in advice)


def test_cupday_uses_compact_checkin_query_and_direct_actions():
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    block = source[source.index('if admin_page == "Cupdagen":'):source.index('if admin_page == "Cupverktyg":')]
    assert 'build_matchday_readiness_advice' in block
    assert 'SELECT id,checked_in FROM teams WHERE tournament_id=?' in block
    assert 'Inför nästa avspark' in block
    assert 'Kontrollera lagincheckning' in block
    assert 'Bemanna matchen' in block
