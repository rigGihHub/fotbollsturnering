from pathlib import Path

VERSION = "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_release_version():
    root = Path(__file__).resolve().parents[1]
    assert (root / "VERSION.txt").read_text().strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in (root / "app.py").read_text()


def test_first_run_wizard_has_consequence_preview_and_capacity_guard():
    root = Path(__file__).resolve().parents[1]
    source = (root / "cupnavi_core" / "new_tournament_wizard.py").read_text()
    assert "setup_consequence_preview" in source
    assert 'm3.metric("Cirka matcher"' in source
    assert 'm4.metric("Matchtid på plan"' in source
    assert 'capacity_ok = preview["margin_tone"] != "over"' in source
    assert "Detta är en kapacitetskontroll, inte det färdiga schemat" in source
