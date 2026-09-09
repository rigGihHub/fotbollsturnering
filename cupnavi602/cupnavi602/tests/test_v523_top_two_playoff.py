from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")

def test_top_two_playoff_is_selectable_in_both_setup_surfaces():
    assert 'TOP_TWO_PLAYOFF_FORMAT = "Slutspel – bara ettor och tvåor"' in APP
    assert 'TOP_TWO_PLAYOFF_FORMAT, "A- och B-slutspel"' in APP
    assert '"Slutspel – bara ettor och tvåor", "A- och B-slutspel"' in SETUP

def test_top_two_playoff_only_uses_rank_one_and_two_sources():
    start = APP.index('if fmt == TOP_TWO_PLAYOFF_FORMAT:')
    end = APP.index('if fmt == "A- och B-slutspel":', start)
    block = APP[start:end]
    assert ':1"' in block and ':2"' in block
    assert ':3"' not in block and ':4"' not in block
    assert 'len(groups) not in {2, 4, 8}' in block
    assert 'return [("Slutspel", len(sources), sources)], ""' in block
