from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v301_release_and_navigation_contract():
    assert VERSION == "2026.08.29-302-PUBLIC-MATCH-EVENT-ROBUSTNESS"
    assert "from urllib.parse import urljoin" in E2E
    assert 'href=button.get_attribute("href")' in E2E
    assert 'assert href and f"section={section}" in href' in E2E
    assert 'page.goto(urljoin(BASE,href),wait_until="domcontentloaded",timeout=60000)' in E2E
    assert 'button.click()' not in E2E[E2E.index("section_contracts = ["):E2E.index("overflow=page.evaluate")]
