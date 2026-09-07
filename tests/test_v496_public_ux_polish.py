from pathlib import Path

VERSION = "2026.09.07-499-DOCUMENT-TO-COMPLETE-PROPOSAL"
APP = Path("app.py").read_text(encoding="utf-8")
FILTERS = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
INFO = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")


def test_version_consistency():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in Path("cupnavi_core/version.py").read_text()


def test_clock_has_room_for_full_card():
    assert "components.html(clock_html, height=98, scrolling=False)" in APP
    assert "box-sizing:border-box" in APP


def test_accessibility_control_is_pinned_to_lower_left_on_desktop():
    assert 'bottom:10px!important;width:248px!important' in APP
    assert 'font-size:10px!important' in APP


def test_primary_public_navigation_never_wraps_labels():
    nav_block = STYLE[STYLE.index('[class*="st-key-cn_public_primary_nav_shell_"]'):]
    assert "white-space:nowrap!important" in nav_block
    assert "white-space:normal!important" not in nav_block[:6000]


def test_event_details_toggle_lives_inside_filter_and_not_below_it():
    assert '"⚽ Målskyttar och kort"' in FILTERS
    assert 'key=f"public_match_events_v444_{tournament_id}"' in FILTERS
    assert 'show_match_events = st.toggle(' not in MATCHES
    assert 'st.session_state.get(_events_toggle_key, True)' in MATCHES
    assert "show_event_details_toggle=any((" in WORKSPACE


def test_venue_cards_match_practical_card_structure():
    assert ".cn-venue-card,.cn-practical-item{display:grid" in INFO
    venue_build = INFO[INFO.index("if venue_points_public:"):INFO.index("st.markdown(f\"<div class='cn-info-section-title'>📍")]
    assert venue_build.index("<small>") < venue_build.index("<strong>")


def test_share_popover_is_compact_and_non_scrolling():
    assert '[data-testid="stPopoverBody"]:has(.cn-share-popover-marker){max-height:none!important;overflow:visible!important' in APP
    share = APP[APP.index('with st.popover("Dela"'):APP.index('@st.cache_data(show_spinner=False)')]
    assert "width=76" in share
    assert "st.divider()" not in share
    assert "Länken går till den publika cupsidan" not in share
