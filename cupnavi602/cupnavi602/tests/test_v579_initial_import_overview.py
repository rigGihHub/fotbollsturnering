from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "cupnavi_core/cup_document_creator_view.py").read_text()
VER = (ROOT / "cupnavi_core/version.py").read_text()


def test_version():
    assert "579-INITIAL-IMPORT-OVERVIEW" in VER


def test_overview_is_review_first_not_fake_import_status():
    assert "Importöversikt" in DOC
    assert "✓ betyder hittat – inte att uppgiften redan är sparad" in DOC
    assert "granskar och använder varje del i rätt setupsteg" in DOC


def test_overview_covers_setup_sections():
    for label in ["Cupinfo", "Lag", "Grupper", "Regler", "Planer", "Schema", "Slutspel"]:
        assert f'"label": "{label}"' in DOC


def test_overview_surfaces_found_and_missing_separately():
    assert "Hittat i underlaget:" in DOC
    assert "Behöver kompletteras senare:" in DOC


def test_overview_counts_actual_extracted_content():
    assert 'len(teams)' in DOC
    assert 'len(groups)' in DOC
    assert 'len(venues)' in DOC
    assert 'len(matches)' in DOC
    assert 'len(playoffs)' in DOC
    assert 'rule_values' in DOC


def test_warnings_remain_visible():
    assert "behöver kontrolleras i underlaget innan du går vidare" in DOC
