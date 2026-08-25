from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_segmented_controls_have_explicit_light_inactive_style():
    text = app_text()
    assert '[data-testid="stSegmentedControl"] button' in text
    assert '[data-testid="stButtonGroup"] button' in text
    assert 'background:#F8FAFC !important;' in text
    assert 'color:#172033 !important;' in text


def test_segmented_controls_have_light_green_selected_style():
    text = app_text()
    assert 'button[aria-pressed="true"]' in text
    assert 'button[aria-checked="true"]' in text
    assert '[data-selected="true"]' in text
    assert 'background:#DCFCE7 !important;' in text
    assert 'color:#14532D !important;' in text


def test_public_segmented_controls_still_exist():
    text = app_text()
    assert 'match_view = st.segmented_control(' in text
    assert 'stats_section = st.segmented_control(' in text
