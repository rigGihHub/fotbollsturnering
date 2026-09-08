from pathlib import Path

FILTERS = Path("cupnavi_core/public_match_filters_view.py").read_text()
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text()
APP = Path("app.py").read_text()


def test_weather_is_opt_in_on_first_public_match_paint():
    block = FILTERS[FILTERS.index('show_weather = display_col1.toggle('):FILTERS.index('if show_event_details_toggle:')]
    assert 'value=False' in block


def test_match_events_are_opt_in_on_first_public_match_paint():
    toggle = FILTERS[FILTERS.index('display_col2.toggle('):FILTERS.index('return (')]
    assert 'value=False' in toggle
    assert 'st.session_state.get(_events_toggle_key, False)' in MATCHES


def test_v528_version_is_exposed():
    assert '2026.09.07-528-PUBLIC-FIRST-PAINT-SECONDARY-DATA-DEFER' in APP
    assert Path('VERSION.txt').read_text().strip() == '2026.09.07-528-PUBLIC-FIRST-PAINT-SECONDARY-DATA-DEFER'
