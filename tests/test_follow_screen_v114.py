from pathlib import Path

def text():
    return Path('app.py').read_text(encoding='utf-8')

def test_public_follow_team_and_screen_mode_exist():
    t=text()
    assert '"⭐ Följ mitt lag"' in t
    assert 'screen_mode = bool' in t
    assert 'Informationsskärm' in t
    assert 'window.parent.location.reload()' in t
    assert 'screen=1' in t

def test_screen_mode_keeps_live_upcoming_results_and_tables():
    t=text()
    assert 'Pågår / nu' in t
    assert 'Kommande' in t
    assert 'Senaste resultat' in t
    assert '_screen_table_bundle = calculate_all_group_tables(tournament_id, tournament)' in t
    assert 'screen_groups = _screen_table_bundle["groups"][:4]' in t
