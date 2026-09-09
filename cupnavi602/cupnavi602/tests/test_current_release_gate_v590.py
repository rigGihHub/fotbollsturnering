from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_v590_version_and_group_ux_contract():
    assert "2026.09.09-590-GROUP-FLOW-UX-PASS" in APP
    assert "1. Välj hur grupperna ska skapas" in APP
    assert "2. Kontrollera gruppindelningen" in APP
    assert "Din uppgift på den här sidan" in APP
    assert "Rekommenderat · CupNavi gör ett första förslag" in APP
    assert "Fortsätt till Regler →" in APP

def test_v590_keeps_import_and_manual_paths():
    for text in ["📦 Från första importen", "✨ CupNavi föreslår", "📷 Importera nytt foto", "✋ Gör själv"]:
        assert text in APP

def test_v590_keeps_group_history_protection():
    assert "production_history_locked(tid, tournament)" in APP
    assert "Gruppstrukturen är låst efter första resultatet" in APP
