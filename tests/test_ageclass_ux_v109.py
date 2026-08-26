from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_age_classes_are_modeled_and_filtered():
    assert "competition_classes(" in APP
    assert "Tävlingsklasser" in APP
    lag_start = APP.index('if admin_page == "Lag":')
    lag_end = APP.index('if admin_page == "Grupper":', lag_start)
    lag = APP[lag_start:lag_end]
    assert '"Tävlingsklass"' in lag
    assert "Hantera tävlingsklasser i Adminöversikt" in lag
