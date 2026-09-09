from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
STYLE=(ROOT/'cupnavi_core/style_system.py').read_text(encoding='utf-8')

def test_v568_version_contract():
    assert (ROOT/'VERSION.txt').read_text().strip() == '2026.09.08-568-MOBILE-ADMIN-STEPPER'
    assert '2026.09.08-568-MOBILE-ADMIN-STEPPER' in APP

def test_mobile_first_screen_uses_compact_stepper():
    assert 'admin_flow_mobile_' in APP
    assert '← {_prev_label}' in APP
    assert '{_next_label} →' in APP
    assert 'popover("Alla 9 steg"' in APP

def test_all_nine_steps_remain_directly_accessible():
    assert 'admin_mobile_all_step_' in APP
    assert 'for _idx, (_step_label, _target_page) in enumerate(_BEGINNER_JOURNEY, start=1)' in APP
    assert 'admin_full_flow_desktop_' in APP

def test_responsive_shell_switch_is_css_only():
    assert '[class*="st-key-admin_flow_mobile_"]{display:none!important}' in STYLE
    assert '[class*="st-key-admin_full_flow_desktop_"]{display:none!important}' in STYLE
    assert '[class*="st-key-admin_flow_mobile_"]{display:block!important' in STYLE

def test_v567_safe_schedule_choice_survives():
    assert 'Behåll och granska befintligt schema' in (ROOT/'cupnavi_core/schedule_workspace_view.py').read_text(encoding='utf-8')
