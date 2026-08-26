from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_competition_classes_use_fixed_picker_not_free_text():
    # Class creation lives in setup/Admin overview and still uses fixed choices.
    assert 'setup_class_category_' in APP
    assert 'setup_class_year_' in APP
    assert 'YOUTH_CLASS_CATEGORIES' in APP
    assert 'YOUTH_CLASS_YEARS' in APP
    lag_start = APP.index('if admin_page == "Lag":')
    lag_end = APP.index('if admin_page == "Grupper":', lag_start)
    lag = APP[lag_start:lag_end]
    assert 'new_team_competition_class_' in lag
    assert 'manage_class_category_' not in lag
