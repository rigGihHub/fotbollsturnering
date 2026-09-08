from pathlib import Path

APP = Path('app.py').read_text()


def _public_core_loader_block():
    start = APP.index('def public_core_snapshot(')
    end = APP.index('\ndef run_many(', start)
    return APP[start:end]


def test_public_core_fuses_match_and_team_first_paint_reads():
    block = _public_core_loader_block()
    fused_start = block.index('if include_matches and include_teams:')
    fallback_start = block.index('else:', fused_start)
    fused = block[fused_start:fallback_start]
    assert "SELECT 'match' AS row_kind" in fused
    assert "SELECT 'team' AS row_kind" in fused
    assert 'UNION ALL' in fused
    assert fused.count('con.execute(') == 1
    assert '(tournament_id, tournament_id)' in fused


def test_fused_rows_are_split_back_into_normal_match_and_team_shapes():
    block = _public_core_loader_block()
    assert "_row_value(row, 'row_kind', '') == 'match'" in block
    assert 'matches.append({column:' in block
    assert 'teams.append({column:' in block
    assert "'referee_name','pitch_name'" in block
    assert "'primary_color','secondary_color'" in block


def test_single_projection_routes_keep_their_targeted_queries():
    block = _public_core_loader_block()
    assert 'if include_matches:' in block
    assert 'if include_teams:' in block
    assert 'FROM teams WHERE tournament_id=? ORDER BY name' in block


def test_v530_version_is_exposed():
    version = '2026.09.07-530-PUBLIC-CORE-FUSED-READ'
    assert version in APP
    assert Path('VERSION.txt').read_text().strip() == version
