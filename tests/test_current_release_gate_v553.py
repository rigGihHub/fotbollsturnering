from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
NAV = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")
SMART = (ROOT / "cupnavi_core" / "smart_image_import.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_release_files_are_synchronized():
    assert VERSION == "2026.09.08-553-REFEREE-MISC-SMART-IMPORT"
    assert VERSION in CORE_VERSION


def test_referee_is_own_optional_primary_step():
    assert '("Domare", "Domare")' in APP
    assert 'FLOW_STEPS = ["Cupinfo", "Lag", "Grupper", "Regler", "Planer & tider", "Domare", "Schema", "Kontroll", "Publicera"]' in NAV
    assert 'Steg 6 av 9 · Domare' in APP
    assert 'blockerar aldrig fortsatt arbete' in APP


def test_misc_is_outside_numbered_flow():
    assert 'if admin_page == "Övrigt":' in APP
    assert 'Övrigt · frivilligt' in APP
    assert 'Sponsorer' in APP and 'Besöksstatistik' in APP
    assert '("Övrigt", "Övrigt")' not in APP


def test_image_import_discovers_then_asks_before_write():
    assert 'Vad vill du lyfta in i CupNavi?' in APP
    assert 'inget skrivs in automatiskt' in APP
    assert 'detect_importable_sections' in APP
    assert 'Gissa aldrig saknade värden' in SMART
    assert 'sections' in SMART and 'confidence' in SMART
