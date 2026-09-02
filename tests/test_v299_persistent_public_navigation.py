from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_public_navigation_sticks_via_streamlit_element_wrapper():
    assert '[data-testid="stElementContainer"]:has(.cn-public-section-nav)' in STYLE
    assert '.element-container:has(.cn-public-section-nav)' in STYLE
    assert 'position:sticky !important;top:0 !important;z-index:999995 !important' in STYLE
    assert '.cn-public-section-nav{' in STYLE
    assert 'position:relative !important;top:auto !important;z-index:1 !important' in STYLE


def test_existing_public_navigation_visual_contract_is_preserved():
    assert 'grid-template-columns:repeat(5,minmax(0,1fr)) !important' in STYLE
    assert 'background:#1f6f4a !important' in STYLE
    assert '.cn-public-section-nav a.active{background:#ffffff !important;color:#14552f !important' in STYLE


def test_v299_release_is_canonical():
    expected = '2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP'
    assert (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip() == expected
    assert expected in APP
    assert expected in (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')
