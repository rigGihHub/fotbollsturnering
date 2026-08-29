from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_v130_version_and_dashboard_cleanup():
    assert 'APP_BUILD_VERSION = ' in APP
    assert 'Kopiera/öppna publik länk' not in APP
    assert 'Delning sköts via den integrerade Dela cupen-knappen' not in APP
    assert 'Här ställer du in cupens grunduppgifter' not in APP
    assert '🔗 Öppna publik vy' in APP


def test_next_step_uses_real_newlines_not_literal_escape_text():
    assert 'st.info(f"**{next_step.title}**\\n\\n{next_step.text}")' in APP
    assert 'st.info(f"**{next_step.title}**\\\\n\\\\n{next_step.text}")' not in APP


def test_optional_info_textareas_are_progressively_disclosed():
    start = APP.index('if edited_medical:')
    end = APP.index('st.markdown("#### Poängregler och tabell")', start)
    block = APP[start:end]
    assert 'if edited_medical:' in block
    assert 'if edited_lost_found:' in block
    assert 'if edited_accessibility_info:' in block
    # Saved values are preserved while hidden.
    assert 'edited_medical_info = _row_value(tournament, "medical_info", "") or ""' in block
    assert 'edited_lost_found_info = _row_value(tournament, "lost_found_info", "") or ""' in block
    assert 'edited_accessibility_text = _row_value(tournament, "accessibility_info", "") or ""' in block


def test_link_buttons_follow_light_design_system():
    assert '[data-testid="stLinkButton"] a {' in STYLE
    assert 'background:#FFFFFF !important;' in STYLE
