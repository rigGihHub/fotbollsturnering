
from pathlib import Path
import ast
import collections

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def test_legacy_share_renderers_are_removed():
    for symbol in [
        "def share_panel_html(",
        "def render_share_panel(",
        "def qr_share_panel_html(",
        "def render_qr_share_panel(",
        "cn-share-panel-anchor",
        "cn-share-toggle-anchor",
    ]:
        assert symbol not in APP


def test_live_public_share_popover_is_retained():
    start=APP.index("def render_public_share_control(")
    end=APP.index("@st.cache_data(show_spinner=False)",start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "qr_png_bytes(share_url)" in block
    assert "WhatsApp" in block


def test_no_unreferenced_public_top_level_helpers_remain():
    tree=ast.parse(APP)
    counts=collections.Counter(
        node.id for node in ast.walk(tree) if isinstance(node,ast.Name)
    )
    dead=[
        node.name
        for node in tree.body
        if isinstance(node,ast.FunctionDef)
        and not node.name.startswith("_")
        and counts[node.name] == 0
    ]
    assert dead == []
