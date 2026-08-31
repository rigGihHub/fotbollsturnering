from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / 'cupnavi_core' / 'match_reporter_workspace_view.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v324_version():
    assert VERSION == '2026.08.31-354-ADDRESS-READINESS-FIX'


def test_reporter_uses_lazy_section_selector_instead_of_tabs():
    assert 'st.segmented_control(' in WORKSPACE
    assert 'st.tabs([' not in WORKSPACE
    assert 'reporter_workspace_section_' in WORKSPACE
    assert 'if reporter_section == reporter_sections[0]:' in WORKSPACE
    assert 'if reporter_section == reporter_sections[1]:' in WORKSPACE
    assert 'if reporter_section == reporter_sections[2]:' in WORKSPACE
    assert 'if reporter_section == reporter_sections[3]:' in WORKSPACE


def test_score_remains_default_workspace():
    assert 'default=reporter_sections[0]' in WORKSPACE
    assert 'deps.translate("CupNavi Score")' in WORKSPACE
