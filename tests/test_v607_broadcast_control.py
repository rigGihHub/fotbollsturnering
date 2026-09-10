from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")

EXPECTED = "2026.09.09-607-BROADCAST-CONTROL-VISUAL-REBUILD"


def test_release_identifiers_are_synchronized():
    assert VERSION == EXPECTED
    assert EXPECTED in APP
    assert f'APP_VERSION = "{EXPECTED}"' in CORE


def test_main_canvas_is_explicitly_owned_by_cupnavi():
    assert '[data-testid="stMain"]' in APP
    assert '[data-testid="stMainBlockContainer"]' in APP
    assert '--bc-canvas:#07111a' in APP


def test_native_white_islands_are_normalized():
    for selector in ('stVerticalBlockBorderWrapper', 'stForm', 'stExpander', 'stMetric'):
        assert selector in APP
    assert '--bc-panel:#0d1c27' in APP


def test_sidebar_and_header_share_dark_shell():
    assert '[data-testid="stSidebar"]' in APP
    assert '[data-testid="stHeader"]' in APP
    assert 'background:#061019!important' in APP


def test_texttv_keeps_independent_black_layer():
    assert '.cn-texttv-table' in APP
    assert 'background:#010405!important' in APP
