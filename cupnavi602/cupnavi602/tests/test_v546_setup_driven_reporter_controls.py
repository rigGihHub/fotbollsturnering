from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTER = (ROOT / 'cupnavi_core' / 'match_reporter_workspace_view.py').read_text()
VERSION = (ROOT / 'VERSION.txt').read_text().strip()


def test_v546_version():
    assert VERSION == '2026.09.08-546-SETUP-DRIVEN-REPORTER-CONTROLS'


def test_reporter_sections_follow_setup_flags():
    assert '_setup_player_events = _setup_scorers or _setup_assists or _setup_cards' in REPORTER
    assert 'if _setup_player_events:\n        reporter_sections.append(_events_section)' in REPORTER
    assert 'if reporter_section == _events_section and _setup_player_events:' in REPORTER


def test_each_player_event_control_is_individually_gated():
    assert 'if _scorer_tracking:' in REPORTER
    assert 'if _assist_tracking:' in REPORTER
    assert 'if _card_tracking:' in REPORTER
    assert 'if scorer_enabled:' in REPORTER
    assert 'if assist_enabled:' in REPORTER
    assert 'if card_statistics_enabled:' in REPORTER
    assert 'if not scorer_enabled and "Mål" in reporter_columns' in REPORTER


def test_reporter_missing_flag_defaults_do_not_expose_optional_events():
    assert 'deps.row_value(tournament, "enable_scorer_leaderboard", 0)' in REPORTER
    assert 'deps.row_value(tournament, "enable_assist_leaderboard", 0)' in REPORTER
    assert 'deps.row_value(tournament, "enable_card_statistics", 0)' in REPORTER
