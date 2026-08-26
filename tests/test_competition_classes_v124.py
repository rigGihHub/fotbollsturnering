from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_competition_class_language_and_hierarchy_are_visible():
    assert "Tävlingsklasser" in APP
    assert "Planerade lag" in APP
    assert "competition_class_label" in APP
    lag_start = APP.index('if admin_page == "Lag":')
    lag_end = APP.index('if admin_page == "Grupper":', lag_start)
    lag = APP[lag_start:lag_end]
    assert "Tävlingsklasser definieras i Adminöversikten" in lag
