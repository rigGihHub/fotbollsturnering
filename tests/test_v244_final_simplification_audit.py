
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def test_admin_search_is_after_navigation():
    search=APP.index('with st.expander("Sök i cupen", expanded=False):')
    nav=APP.index('_ADMIN_PRIMARY_PAGES_BY_GROUP = {')
    page=APP.index('admin_page = st.session_state[admin_page_key]')
    assert nav < search < page
    assert 'with st.expander("🔎 Sök i cupen", expanded=False):' not in APP


def test_primary_navigation_labels_are_shorter_and_consistent():
    nav=APP[APP.index("ADMIN_NAV_GROUPS = ["):APP.index("ADMIN_NAV = [")]
    assert '("Cupinställningar", "Inställningar")' in nav
    assert '("Matcher och resultat", "Resultat")' in nav
    assert '("Önskemålscentral", "Önskemål")' in nav
    assert '("Cupverktyg", "Verktyg")' in nav
    assert '("Problem & lösningar", "Problem")' in nav
    assert '("Instruktioner", "Guide")' in nav


def test_flow_context_no_longer_duplicates_page_title_and_copy():
    block=APP[APP.index('_flow_index = _primary_flow_index(admin_page)'):APP.index('if int(_flow_counts["teams_n"] or 0) == 0:')]
    assert "cn-flow-context-compact" in block
    assert "cn-flow-title" not in block
    assert "cn-flow-copy" not in block
    assert 'if _flow_index is not None:' in block


def test_recommended_next_step_only_renders_in_primary_flow():
    start=APP.index('if int(_flow_counts["teams_n"] or 0) == 0:')
    end=APP.index('current_schedule_dirty =',start)
    block=APP[start:end]
    assert 'if _flow_index is not None and admin_page != _recommended_page:' in block
    assert '<b>Nästa steg</b>' in block


def test_core_workflow_pages_remain_unchanged_as_routes():
    for page in [
        "Adminöversikt","Lag","Grupper","Skapa och publicera schema",
        "Matcher och resultat","Tabeller","Slutspel"
    ]:
        assert f'("{page}",' in APP
