from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v301_release_and_navigation_contract():
    assert VERSION == "2026.08.31-348-GUIDED-CUP-SETUP"
    nav_block = E2E[E2E.index("section_contracts = ["):E2E.index("overflow=page.evaluate")]
    assert 'button.click()' in nav_block
    assert 'page.wait_for_url(re.compile(rf"[?&]section={re.escape(section)}(?:&|$)"),timeout=20000)' in nav_block
    assert 'get_attribute("href")' not in nav_block
    assert 'page.goto(urljoin(BASE,href)' not in nav_block
