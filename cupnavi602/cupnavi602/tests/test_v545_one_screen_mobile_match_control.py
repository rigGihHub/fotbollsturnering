from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v545_one_screen_mobile_reporter_contract():
    text = (ROOT / 'cupnavi_core' / 'match_reporter_workspace_view.py').read_text()
    assert '### 🎛️ Matchkontroll' in text
    assert 'reporter_inline_player_' in text
    assert 'inline_goal_plus_' in text and 'inline_goal_minus_' in text
    assert 'inline_assist_plus_' in text and 'inline_assist_minus_' in text
    assert 'inline_yellow_plus_' in text and 'inline_yellow_minus_' in text
    assert 'inline_red_plus_' in text and 'inline_red_minus_' in text
    assert 'Fler matchdetaljer / massinmatning' in text
    assert 'expanded=False' in text
    assert 'REPORTER_CORRECTION_WINDOW_SECONDS = 15' in text
    assert 'REPORTER_NOTIFICATION_DEBOUNCE_SECONDS = 30' in text


def test_v545_large_mobile_controls_and_match_identity():
    text = (ROOT / 'cupnavi_core' / 'match_reporter_workspace_view.py').read_text()
    assert 'min-height: 64px' in text
    assert 'cn-reporter-score-live' in text
    assert 'Aktuell match ·' in text
    assert 'Plan {quick_match' in text


def test_v545_version_synced():
    expected = '2026.09.08-545-ONE-SCREEN-MOBILE-MATCH-CONTROL'
    assert (ROOT / 'VERSION.txt').read_text().strip() == expected
    assert expected in (ROOT / 'cupnavi_core' / 'version.py').read_text()
    assert expected in (ROOT / 'app.py').read_text()
