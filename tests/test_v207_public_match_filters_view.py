from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
FILTER_VIEW=(ROOT/"cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")


def test_filter_ui_is_extracted():
    assert "def render_public_match_filters(" in FILTER_VIEW
    assert 'with st.expander("Filter & visning", expanded=False):' in FILTER_VIEW
    assert 'tr("Välj grupp")' in FILTER_VIEW
    assert 'tr("Välj lag")' in FILTER_VIEW
    assert 'tr("Välj plan")' in FILTER_VIEW


def test_app_keeps_thin_filter_adapter():
    start=WORKSPACE.index("def _filter_public_matches")
    end=WORKSPACE.index("def _render_public_match_cards",start)
    block=WORKSPACE[start:end]
    assert "render_public_match_filters_module(" in block
    assert len(block.splitlines()) < 30


def test_filter_view_delegates_to_pure_filter_logic():
    assert 'filter_matches(' in FILTER_VIEW
    assert 'sort_public_matches(filtered)' in FILTER_VIEW
