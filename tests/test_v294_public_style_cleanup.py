from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v294_release_and_public_style_boundary():
    assert VERSION == "2026.08.31-351-SETUP-COMPLETION-HANDOFF"
    assert "inject_public_experience_styles(st)" in WORKSPACE
    assert ".cn-follow-shell" not in APP
    assert "def inject_public_experience_styles(st):" in STYLE
    assert ".cn-follow-shell" in STYLE
    assert ".cn-live-grid" in STYLE


def test_v294_public_media_queries_are_not_nested():
    start = STYLE.index("def inject_public_experience_styles(st):")
    css = STYLE[start:]
    # The extracted block should expose independent responsive breakpoints rather
    # than the invalid nested @media pattern previously embedded in app.py.
    assert css.count("@media(min-width:901px){") == 1
    assert css.count("@media(max-width:900px){") == 1
    assert css.count("@media(max-width:760px){") == 1
    assert "@media(min-width:901px){\n          .cn-public-follow-anchor" in css
    assert "@media(max-width:900px){\n          .cn-live-grid" in css


def test_v294_public_style_injection_keeps_unsafe_html_contract():
    start = STYLE.index("def inject_public_experience_styles(st):")
    block = STYLE[start:]
    assert "unsafe_allow_html=True" in block
