from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text()

def test_release_version():
    expected = "2026.08.31-351-SETUP-COMPLETION-HANDOFF"
    assert (ROOT / "VERSION.txt").read_text().strip() == expected
    assert expected in (ROOT / "app.py").read_text()

def test_public_navigation_waits_for_new_url_and_domain_content():
    assert 'page.wait_for_url(re.compile(rf"[?&]section={re.escape(section)}(?:&|$)"),timeout=20000)' in E2E
    assert 'page.get_by_text(expected_token,exact=False).first.wait_for(state="visible",timeout=20000)' in E2E
    assert '("Tabeller", "tables", group_token)' in E2E

def test_selectbox_helper_retries_across_streamlit_reruns():
    assert 'while time.time()<deadline:' in E2E
    assert 'combo.click(force=True)' in E2E
    assert '[data-baseweb="popover"]' in E2E
