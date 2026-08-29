from pathlib import Path


def app_text():
    return Path('app.py').read_text(encoding='utf-8')


def screen_text():
    return Path('cupnavi_core/public_shell_view.py').read_text(encoding='utf-8')

def workspace_text():
    return Path('cupnavi_core/public_workspace_view.py').read_text(encoding='utf-8')

def follow_view_text():
    return Path('cupnavi_core/public_team_follow_view.py').read_text(encoding='utf-8')


def test_public_follow_team_and_screen_mode_exist():
    app = app_text()
    screen = screen_text()
    workspace = workspace_text()
    assert '"⭐ Följ mitt lag"' in follow_view_text()
    assert 'screen_mode = bool' in workspace
    assert 'render_public_screen_mode(' in workspace
    assert 'Informationsskärm' in screen
    assert 'window.parent.location.reload()' in screen
    assert 'screen=1' in workspace


def test_screen_mode_keeps_live_upcoming_results_and_tables():
    screen = screen_text()
    assert 'Pågår / nu' in screen
    assert 'Kommande' in screen
    assert 'Senaste resultat' in screen
    assert 'table_bundle = calculate_all_group_tables(tournament_id, tournament)' in screen
    assert 'screen_groups = table_bundle["groups"][:4]' in screen
