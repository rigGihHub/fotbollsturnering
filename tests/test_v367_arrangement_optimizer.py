from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VIEW = (ROOT / 'cupnavi_core' / 'schedule_workspace_view.py').read_text(encoding='utf-8')


def _load():
    spec = importlib.util.spec_from_file_location(
        'schedule_improvement_v367', ROOT / 'cupnavi_core' / 'schedule_improvement.py'
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _matches():
    return [
        {'id': 1, 'stage': 'Gruppspel', 'scheduled_start': '2026-09-01T09:00:00', 'pitch_number': 1, 'referee_id': 1, 'home_source': 'team:1', 'away_source': 'team:2', 'home_score': None, 'away_score': None, 'schedule_locked': 0},
        {'id': 2, 'stage': 'Gruppspel', 'scheduled_start': '2026-09-01T09:30:00', 'pitch_number': 2, 'referee_id': 2, 'home_source': 'team:1', 'away_source': 'team:3', 'home_score': None, 'away_score': None, 'schedule_locked': 0},
        {'id': 3, 'stage': 'Gruppspel', 'scheduled_start': '2026-09-01T12:30:00', 'pitch_number': 1, 'referee_id': 1, 'home_source': 'team:2', 'away_source': 'team:3', 'home_score': None, 'away_score': None, 'schedule_locked': 0},
        {'id': 4, 'stage': 'Gruppspel', 'scheduled_start': '2026-09-01T13:00:00', 'pitch_number': 2, 'referee_id': 2, 'home_source': 'team:1', 'away_source': 'team:2', 'home_score': None, 'away_score': None, 'schedule_locked': 0},
    ]


def test_matchcamp_metrics_include_match_and_opponent_balance():
    mod = _load()
    metrics = mod.schedule_flow_metrics(
        _matches(), match_duration_minutes=20, minimum_rest_minutes=25, arrangement_type='matchcamp'
    )
    assert metrics['arrangement_type'] == 'matchcamp'
    assert metrics['match_count_spread'] == 1
    assert metrics['playtime_spread_minutes'] == 20
    assert metrics['repeated_opponents'] == 1
    assert metrics['maximum_wait'] is not None


def test_matchcamp_penalizes_long_waits_more_than_tournament():
    mod = _load()
    matchcamp = mod.schedule_flow_metrics(
        _matches(), match_duration_minutes=20, minimum_rest_minutes=25, arrangement_type='matchcamp'
    )
    tournament = mod.schedule_flow_metrics(
        _matches(), match_duration_minutes=20, minimum_rest_minutes=25, arrangement_type='tournament'
    )
    assert matchcamp['long_waits'] >= tournament['long_waits']
    assert matchcamp['objective'] > tournament['objective']


def test_optimizer_carries_arrangement_type_through_preview():
    mod = _load()
    proposal = mod.build_schedule_improvement(
        _matches(), match_duration_minutes=20, minimum_rest_minutes=25, arrangement_type='matchcamp'
    )
    assert proposal['arrangement_type'] == 'matchcamp'
    assert proposal['before']['arrangement_type'] == 'matchcamp'
    assert proposal['after']['arrangement_type'] == 'matchcamp'


def test_ui_explains_distinct_matchcamp_and_tournament_goals():
    assert 'Optimera matchcampens flyt' in VIEW
    assert 'Optimera turneringsschemat' in VIEW
    assert 'Skillnad matcher/lag' in VIEW
    assert 'Skillnad speltid' in VIEW
    assert 'Upprepade motstånd' in VIEW
    assert 'arrangement_type=_arrangement_type' in VIEW


def test_matchcamp_apply_skips_home_away_rebalance():
    block = APP[APP.index('def _apply_schedule_improvement'):APP.index('def _save_bulk_schedule_results')]
    assert 'ARRANGEMENT_MATCHCAMP' in block
    assert 'normalize_arrangement_type(arrangement_type) != ARRANGEMENT_MATCHCAMP' in block
    assert 'optimize_group_home_away(tournament_id)' in block


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.03-414-PITCH-TIMING-MODE"' in APP
