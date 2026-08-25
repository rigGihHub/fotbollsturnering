from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_public_metric_says_matches_played():
    text = app_text()
    assert 'tr("Matcher spelade")' in text
    assert 'len(played_matches)' in text and 'len(published_matches)' in text


def test_testdata_has_variable_team_and_group_counts_and_gated_progress():
    text = app_text()
    assert 'Antal testlag' in text
    assert 'Antal testgrupper' in text
    assert 'disabled=not testdata_ready' in text


def test_final_ranking_is_optional_at_creation_and_rendered():
    text = app_text()
    assert 'setup_final_ranking_' in text
    assert 'enable_final_ranking' in text
    assert 'def final_ranking_rows' in text
    assert 'Slutlig ranking' in text


def test_team_can_request_avoiding_latest_group_match():
    text = app_text()
    assert 'Undvik senaste gruppspelsmatchen' in text
    assert 'avoid_late_group_match' in text
    repo = Path("cupnavi_core/schedule_repository.py").read_text(encoding="utf-8")
    assert 'avoid_late_group_match' in repo


def test_new_tournament_enters_setup_wizard():
    text = app_text()
    assert 'new_tournament_setup_id' in text
    assert 'def render_initial_tournament_setup' in text
    assert 'Fortsätt till Admin' in text
    assert 'sparas automatiskt' in text
