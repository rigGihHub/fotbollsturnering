from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")


def test_v130_version_and_dashboard_cleanup():
    assert 'APP_BUILD_VERSION = ' in APP
    assert 'Kopiera/öppna publik länk' not in APP
    assert 'Delning sköts via den integrerade Dela cupen-knappen' not in APP
    assert 'Här ställer du in cupens grunduppgifter' not in APP
    assert '🔗 Öppna publik vy' in APP


def test_next_step_uses_real_newlines_not_literal_escape_text():
    assert 'st.info(f"**{next_step_title}**\\n\\n{next_step_text}")' in APP
    assert 'st.info(f"**{next_step_title}**\\\\n\\\\n{next_step_text}")' not in APP


def test_optional_info_textareas_remain_editable():
    start = APP.index('edited_medical_info = st.text_area')
    end = APP.index('st.markdown("#### Poängregler och tabell")', start)
    block = APP[start:end]
    assert 'disabled=not edited_medical' not in block
    assert 'disabled=not edited_lost_found' not in block
    assert 'disabled=not edited_accessibility_info' not in block
    assert 'Kryssrutan ovan styr endast om informationen visas på infosidan.' in block


def test_link_buttons_follow_light_design_system():
    assert '[data-testid="stLinkButton"] a {' in APP
    assert 'background:#FFFFFF !important;' in APP
