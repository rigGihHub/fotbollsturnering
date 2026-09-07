from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PUB = (ROOT / "cupnavi_core" / "admin_publication.py").read_text(encoding="utf-8")


def test_control_is_status_first_and_routes_blockers():
    assert "Cupen är redo att publiceras" in APP
    assert "er återstår" in APP
    assert "Det här måste fixas" in APP
    assert "Åtgärda →" in APP
    assert "publication_problem_destination(message)" in APP


def test_optional_advice_is_collapsed_and_non_blocking():
    assert "Gula råd och frivilliga förbättringar" in APP
    assert "Det här stoppar inte publicering" in APP


def test_problem_destination_routes_core_blockers():
    assert 'return "Cupinställningar", "Öppna Cupinfo"' in PUB
    assert 'return "Skapa och publicera schema", "Öppna Schema"' in PUB


def test_version_516():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == "2026.09.07-524-PRIMARY-FLOW-PITCH-COUNT-FIX"
