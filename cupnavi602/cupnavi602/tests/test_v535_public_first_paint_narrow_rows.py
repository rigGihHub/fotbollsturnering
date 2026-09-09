from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')


def test_v535_version_and_limited_match_payload_is_narrow():
    assert '2026.09.08-535-PUBLIC-FIRST-PAINT-NARROW-ROWS' in APP
    start = APP.index('if include_matches and include_teams and match_limit is not None and match_window_start and match_window_end:')
    end = APP.index('elif include_matches and include_teams:', start)
    cupday = APP[start:end]
    tuple_start = cupday.index('match_columns=(')
    tuple_end = cupday.index(')', tuple_start)
    cols = cupday[tuple_start:tuple_end]
    for administrative in ("'tournament_id'", "'bracket_id'", "'round_no'", "'referee_id'"):
        assert administrative not in cols
    for required in ("'id'", "'group_id'", "'stage'", "'home_source'", "'away_source'", "'scheduled_start'", "'pitch_name'"):
        assert required in cols


def test_v535_full_match_path_keeps_full_shape_for_fallbacks():
    marker = 'else:\n                if include_matches:'
    start = APP.index(marker, APP.index('def public_core_snapshot'))
    fallback = APP[start:start + 1800]
    assert 'm.tournament_id' in fallback
    assert 'm.bracket_id' in fallback
    assert 'm.round_no' in fallback
    assert 'm.referee_id' in fallback
