from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VER=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_v521_version():
    assert VER == "2026.09.07-524-PRIMARY-FLOW-PITCH-COUNT-FIX"

def test_v521_wide_public_canvas_and_match_hierarchy():
    assert "PUBLIC DESKTOP MATCH FOCUS V521" in APP
    assert "max-width:1540px!important" in APP
    assert "grid-template-columns:120px minmax(0,1fr) 120px!important" in APP
    assert "font-size:clamp(19px,1.25vw,23px)!important" in APP
    assert "font-size:clamp(27px,1.8vw,34px)!important" in APP

def test_v521_preserves_mobile_breakpoint():
    # v521 desktop overrides only begin on wide layouts; existing mobile rules remain authoritative.
    block=APP.split("PUBLIC DESKTOP MATCH FOCUS V521",1)[1].split("SHARE POPOVER POLISH",1)[0]
    assert "@media(min-width:1180px)" in block
    assert "@media(max-width:760px)" not in block
