from pathlib import Path

def test_pitch_availability_copy_is_explicit():
    text = Path("cupnavi_core/new_tournament_wizard.py").read_text(encoding="utf-8")
    assert "När är planerna tillgängliga?" in text
    assert "Starttiden är den första möjliga matchstarten" in text
    assert "Första möjliga matchstart · plan {pitch}" in text
    assert "Planen tillgänglig till · plan {pitch}" in text
