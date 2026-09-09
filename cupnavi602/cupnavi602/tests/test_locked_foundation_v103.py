from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_sport_and_international_foundation_are_selected_at_creation():
    text = app_text()
    creation = text[text.index('def render_new_tournament_creator'):text.index('if view_mode == "Admin":\n    st.sidebar.caption', text.index('def render_new_tournament_creator'))]
    assert '"Sport"' in creation
    assert '"Språk/region"' in creation
    assert '"Tidszon"' in creation
    assert '"Landkod"' in creation
    assert 'locale,timezone_name,participant_type,country_code' in creation
    assert 'grundegenskaper och kan inte ändras' in creation


def test_existing_tournament_foundation_is_read_only():
    text = app_text()
    assert 'Dessa grundinställningar valdes när turneringen skapades och är låsta' in text
    assert 'Spara sport' not in text
    assert 'Spara internationella inställningar' not in text
    assert 'overview_sport_' not in text
    assert 'overview_locale_' not in text
    assert 'overview_timezone_' not in text
    assert 'overview_country_' not in text


def test_logo_is_smaller_than_v102_shell():
    text = app_text()
    assert 'max-width:min(185px, calc(100vw - 28px));' in text
    assert 'width:min(100%, 155px);' in text
    assert 'max-width:170px;' in text
    assert 'width:min(100%, 145px);' in text
