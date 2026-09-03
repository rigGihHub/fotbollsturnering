from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_v393_version():
    assert VERSION == "2026.09.03-414-PITCH-TIMING-MODE"

def test_matchcamp_setup_is_arrangement_specific():
    assert "Grupper och slutspel behövs inte" in VIEW
    assert "Hur många matcher ska varje lag få?" in VIEW
    assert 'c4.metric("Plantid används"' in VIEW
    assert "Minska matcher per lag, lägg till plantid eller använd fler planer" in VIEW

def test_final_review_summarizes_core_choices():
    assert "Här ser du vad du har valt innan du går vidare" in VIEW
    assert "summary_type = arrangement_label(arrangement_type)" in VIEW
    assert "summary_results" in VIEW
