from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
FILTER_VIEW=(ROOT/"cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")

def test_public_match_domain_is_split_by_responsibility():
    for filename in [
        "public_match_cards.py",
        "public_match_filter_logic.py",
        "public_match_feed_logic.py",
        "public_match_filters_view.py",
    ]:
        assert (ROOT/"cupnavi_core"/filename).exists()

def test_main_filter_helper_is_thin_adapter():
    start=WORKSPACE.index("def _filter_public_matches")
    end=WORKSPACE.index("def _render_public_match_cards",start)
    block=WORKSPACE[start:end]
    assert "render_public_match_filters_module(" in block
    assert len(block.splitlines()) < 30

def test_filter_view_preserves_all_filter_modes():
    for token in ['"Tävlingsklass"','tr("En grupp")','tr("Ett lag")','tr("En plan")']:
        assert token in FILTER_VIEW
