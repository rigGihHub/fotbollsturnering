from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_new_tournament_has_checkin_choice_and_persists_it():
    text = app_text()
    assert '"Använd lagincheckning"' in text
    assert 'age_classes_json,enable_team_checkin' in text
    assert '1 if create_team_checkin else 0' in text


def test_checkin_warnings_and_ui_are_gated_by_tournament_setting():
    text = app_text()
    assert '_row_value(tournament, "enable_team_checkin", 1)' in text
    assert 'if teams and bool(_row_value(tournament, "enable_team_checkin", 1)):' in text
    assert 'Lagincheckning används inte i den här turneringen.' in text


def test_team_page_cleanup_contract():
    text = app_text()
    assert 'Formuläret för att lägga till lag är dolt eftersom maxantalet är uppnått.' in text
    assert 'class_options = class_ids if len(class_ids) == 1' in text
    assert 'with st.expander("Tävlingsklasser i turneringen"' not in text
    assert 'st.markdown("#### Tävlingsklasser i turneringen")' in text
