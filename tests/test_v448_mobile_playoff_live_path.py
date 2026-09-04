from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text().strip()
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()


def test_v448_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_mobile_playoff_has_live_status_and_progress_path():
    assert 'return "Pågår", " live"' in PRESENTATION
    assert 'return "Paus", " halftime"' in PRESENTATION
    assert 'return "Slut", " finished"' in PRESENTATION
    assert 'return "Kommande", " upcoming"' in PRESENTATION
    assert 'Vinnaren går vidare till' in PRESENTATION
    assert 'Vinnaren tar guldet' in PRESENTATION


def test_mobile_rounds_show_match_count_and_status_badge():
    assert "round_progress =" in PRESENTATION
    assert "class='round-head'" in PRESENTATION
    assert "html.escape(status_label)" in PRESENTATION
    assert ".cn-playoff-mobile-match.live" in PRESENTATION


def test_mobile_playoff_improvement_adds_no_database_roundtrip():
    start = PRESENTATION.index("def _mobile_status")
    end = PRESENTATION.index("bronze_matches =", start)
    block = PRESENTATION[start:end]
    assert "all_rows(" not in block
    assert "one_row(" not in block
