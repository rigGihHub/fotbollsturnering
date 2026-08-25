from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_competition_classes_use_fixed_picker_not_free_text():
    text = app_text()
    assert 'YOUTH_CLASS_CATEGORIES = {"Pojkar": "P", "Flickor": "F"}' in text
    assert 'YOUTH_CLASS_YEARS = list(range(2008, 2023))' in text
    assert 'setup_class_category_' in text
    assert 'setup_class_year_' in text
    assert 'manage_class_category_' in text
    assert 'manage_class_year_' in text
    assert 'new_tournament_age_classes' not in text
    assert 'manage_competition_classes_' not in text


def test_competition_classes_can_be_removed_safely():
    text = app_text()
    assert 'def remove_competition_class(' in text
    assert 'Ta bort' in text
    assert 'används av {team_count} lag och {group_count} grupper' in text
    assert 'DELETE FROM competition_classes' in text
